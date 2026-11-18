#!/usr/bin/env python3
"""Publish one queued Firestore post per local day at the user's saved time.

Reads the existing paths:
  users/{uid}/settings/automation
  users/{uid}/posts/{postId}

The worker deliberately never reads the Meta access token from Firestore. The
Meta token is supplied only through a GitHub Actions secret. It creates a
server-only daily lock under users/{uid}/automationRuns/{YYYY-MM-DD}; the
current Firestore rules deny client access to that path by default.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_PROJECT_ID = "mana-tech-autopilot"
# Must match firebase-applet-config.json's firestoreDatabaseId in the webpage.
DEFAULT_DATABASE_ID = "ai-studio-manatechautopilo-22439fc5-b3f5-486b-aa04-e698e36833f9"
DEFAULT_API_VERSION = "v27.0"
CAPTION_LIMIT = 2200
MAX_CONTAINER_POLLS = 12
CONTAINER_POLL_SECONDS = 5
MAX_SAFE_RETRIES = 3


class SchedulerError(RuntimeError):
    pass


class GraphAPIError(SchedulerError):
    pass


def parse_local_schedule(settings: dict[str, Any], now_utc: datetime | None = None) -> tuple[datetime, str, bool]:
    """Return local now, local date and whether the configured post time is due."""
    timezone_name = str(settings.get("timeZone") or "UTC").strip()
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise SchedulerError(f"Unknown timezone in Firebase settings: {timezone_name}") from exc

    post_time = str(settings.get("postTime") or "09:00").strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", post_time):
        raise SchedulerError(f"Invalid postTime in Firebase settings: {post_time!r}")
    target_time = datetime.strptime(post_time, "%H:%M").time()

    current = now_utc or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local_now = current.astimezone(zone)
    due = local_now.time().replace(tzinfo=None) >= target_time

    start_date_raw = str(settings.get("startDate") or "").strip()
    if start_date_raw:
        try:
            start_date = date.fromisoformat(start_date_raw)
        except ValueError as exc:
            raise SchedulerError(f"Invalid startDate in Firebase settings: {start_date_raw!r}") from exc
        if local_now.date() < start_date:
            due = False

    return local_now, local_now.date().isoformat(), due


def build_caption(post: dict[str, Any]) -> str:
    title = str(post.get("title") or "").strip()
    caption = str(post.get("caption") or "").strip()
    tags_raw = post.get("hashtags") or []
    if not isinstance(tags_raw, list):
        raise SchedulerError("Post hashtags field must be a list.")

    tags: list[str] = []
    for raw in tags_raw:
        tag = str(raw).strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + tag
        if not re.fullmatch(r"#[\w]+", tag, flags=re.UNICODE):
            raise SchedulerError(f"Invalid hashtag in post {post.get('id')!r}.")
        tags.append(tag)

    parts = [part for part in (title, caption, " ".join(tags)) if part]
    result = "\n\n".join(parts)
    if not result:
        raise SchedulerError(f"Post {post.get('id')!r} has an empty caption.")
    if len(result) > CAPTION_LIMIT:
        raise SchedulerError(
            f"Post {post.get('id')!r} caption is {len(result)} characters; Instagram limit is {CAPTION_LIMIT}."
        )
    return result


def validate_post(post: dict[str, Any]) -> tuple[str, str]:
    post_id = str(post.get("id") or "").strip()
    image_url = str(post.get("imageUrl") or "").strip()
    if not post_id:
        raise SchedulerError("A scheduled Firestore post has no document ID.")
    if not image_url.startswith("https://"):
        raise SchedulerError(f"Post {post_id} needs a publicly reachable HTTPS imageUrl.")
    caption = build_caption(post)
    return image_url, caption


def find_active_settings(db: Any, required_uid: str | None = None) -> tuple[str, dict[str, Any]] | None:
    """Find exactly one valid active automation settings doc; fail closed if ambiguous."""
    matches: list[tuple[str, dict[str, Any]]] = []
    for snap in db.collection_group("settings").stream():
        segments = snap.reference.path.split("/")
        if len(segments) != 4 or segments[0] != "users" or segments[2:] != ["settings", "automation"]:
            continue
        uid = segments[1]
        data = snap.to_dict() or {}
        if required_uid and uid != required_uid:
            continue
        if data.get("ownerId") != uid:
            continue
        if data.get("autoPostEnabled") is True and data.get("instagramEnabled") is True:
            matches.append((uid, data))

    if not matches:
        return None
    if len(matches) > 1:
        raise SchedulerError(
            "More than one active Instagram automation settings document exists. "
            "Set the FIREBASE_OWNER_UID GitHub secret to the intended user UID."
        )
    return matches[0]


def _request_graph(method: str, edge: str, params: dict[str, str], api_version: str) -> dict[str, Any]:
    url = f"https://graph.facebook.com/{api_version}/{edge.lstrip('/')}"
    encoded = urlencode(params).encode("utf-8")
    if method.upper() == "GET":
        url = f"{url}?{encoded.decode('ascii')}"
        body = None
    else:
        body = encoded

    request = Request(
        url,
        data=body,
        method=method.upper(),
        headers={
            "User-Agent": "ManaTechFirestoreScheduler/1.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise GraphAPIError(f"Meta returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError) as exc:
        # The caller decides whether a failure is safe to retry based on the phase.
        raise GraphAPIError(f"Network error contacting Meta ({type(exc).__name__}).") from None

    if not isinstance(payload, dict):
        raise GraphAPIError("Meta returned an unexpected response.")
    if payload.get("error"):
        error = payload["error"]
        code = error.get("code", "unknown") if isinstance(error, dict) else "unknown"
        message = error.get("message", "Unknown Graph API error") if isinstance(error, dict) else "Unknown Graph API error"
        raise GraphAPIError(f"Meta Graph API error {code}: {message}")
    return payload


def _select_oldest_scheduled_post(db: Any, uid: str) -> tuple[Any, dict[str, Any]] | None:
    post_refs = db.collection("users").document(uid).collection("posts")
    candidates: list[tuple[float, Any, dict[str, Any]]] = []
    for snap in post_refs.stream():
        data = snap.to_dict() or {}
        if data.get("ownerId") != uid or data.get("status") != "scheduled":
            continue
        platforms = data.get("platforms") or []
        if not isinstance(platforms, list) or "instagram" not in platforms:
            continue
        created = data.get("createdAt")
        if isinstance(created, datetime):
            created_epoch = created.timestamp()
        elif hasattr(created, "timestamp"):
            created_epoch = created.timestamp()
        else:
            created_epoch = 0.0
        candidates.append((created_epoch, snap.reference, {**data, "id": snap.id}))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[2]["id"]))
    _, ref, data = candidates[0]
    return ref, data


def _mark_post_failed(post_ref: Any, message: str, firestore_module: Any) -> None:
    try:
        post_ref.update({
            "status": "failed",
            "errorMessage": message[:500],
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        })
    except Exception as exc:  # do not hide the original publication failure
        print(f"WARNING: could not record failed status in Firestore ({type(exc).__name__}).")


def _poll_container(creation_id: str, token: str, api_version: str) -> str:
    for attempt in range(MAX_CONTAINER_POLLS):
        result = _request_graph(
            "GET", creation_id,
            {"fields": "status_code", "access_token": token},
            api_version,
        )
        status = str(result.get("status_code") or "UNKNOWN").upper()
        print(f"Instagram media container status: {status}")
        if status == "FINISHED":
            return "FINISHED"
        if status in {"ERROR", "EXPIRED"}:
            return status
        if attempt < MAX_CONTAINER_POLLS - 1:
            time.sleep(CONTAINER_POLL_SECONDS)
    return "IN_PROGRESS"


def run_scheduler(db: Any, firestore_module: Any, token: str, api_version: str,
                  ig_user_id_override: str = "", required_uid: str = "", dry_run: bool = False,
                  now_utc: datetime | None = None) -> int:
    active = find_active_settings(db, required_uid.strip() or None)
    if active is None:
        print("No active Instagram automation settings document found; nothing to do.")
        return 0
    uid, settings = active

    local_now, local_day, due = parse_local_schedule(settings, now_utc)
    print(
        f"Schedule check: {local_now.strftime('%Y-%m-%d %H:%M:%S %Z')} | "
        f"target {settings.get('postTime', '09:00')} {settings.get('timeZone', 'UTC')}"
    )
    if not due:
        print("The saved start date or custom posting time has not arrived; skipping.")
        return 0

    ig_user_id = ig_user_id_override.strip() or str(settings.get("instagramAccountId") or "").strip()
    if not ig_user_id:
        raise SchedulerError("Missing Instagram account ID. Set META_IG_USER_ID or save instagramAccountId in the page settings.")
    if not token and not dry_run:
        raise SchedulerError("Missing META_ACCESS_TOKEN GitHub secret.")

    lock_ref = db.collection("users").document(uid).collection("automationRuns").document(local_day)
    lock_snap = lock_ref.get()
    lock = lock_snap.to_dict() if lock_snap.exists else None

    if lock and lock.get("status") in {"published", "uncertain"}:
        print(f"Daily lock is {lock.get('status')} for {local_day}; no duplicate will be attempted.")
        return 0

    post_ref = None
    post = None
    if lock and lock.get("postId"):
        post_ref = db.collection("users").document(uid).collection("posts").document(str(lock["postId"]))
        post_snap = post_ref.get()
        if post_snap.exists:
            post = {**(post_snap.to_dict() or {}), "id": post_snap.id}
    if post is None:
        selected = _select_oldest_scheduled_post(db, uid)
        if selected is None:
            print("No scheduled Instagram posts in this user's Firestore queue; skipping without generating a post.")
            return 0
        post_ref, post = selected

    image_url, caption = validate_post(post)
    print(f"Eligible post: {post['id']} — {post.get('title', '(untitled)')}")
    if dry_run:
        print("DRY RUN: would publish this Firestore post; no Meta API or Firestore writes performed.")
        return 0

    current_status = str((lock or {}).get("status") or "")
    phase = str((lock or {}).get("phase") or "")
    attempts = int((lock or {}).get("attempts") or 0)

    if current_status == "publishing":
        lock_ref.update({"status": "uncertain", "updatedAt": firestore_module.SERVER_TIMESTAMP,
                         "error": "Previous publish request had an uncertain outcome; verify Instagram manually."})
        _mark_post_failed(post_ref, "Instagram publish outcome is uncertain. Check the Instagram account before retrying.", firestore_module)
        print("Previous run stopped during media_publish. Marked uncertain; not retrying to avoid duplicates.")
        return 1

    if phase == "container_ready" and str((lock or {}).get("creationId") or ""):
        creation_id = str(lock["creationId"])
        print(f"Resuming existing media container for {post['id']}.")
    else:
        if current_status in {"creating_container", "retryable"}:
            previous_started = (lock or {}).get("updatedAt") or (lock or {}).get("startedAt")
            if isinstance(previous_started, datetime):
                age = (datetime.now(timezone.utc) - previous_started.replace(tzinfo=timezone.utc)
                       if previous_started.tzinfo is None else datetime.now(timezone.utc) - previous_started.astimezone(timezone.utc)).total_seconds()
                if current_status == "creating_container" and age < 15 * 60:
                    print("Another run is still preparing the media container; skipping this poll.")
                    return 0
            if attempts >= MAX_SAFE_RETRIES:
                print("Safe pre-publish retries are exhausted for today; manual review is required.")
                return 1
        attempts += 1
        lock_payload = {
            "ownerId": uid,
            "localDate": local_day,
            "postId": post["id"],
            "status": "creating_container",
            "phase": "container_create",
            "attempts": attempts,
            "startedAt": firestore_module.SERVER_TIMESTAMP,
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        }
        if lock_snap.exists:
            lock_ref.set(lock_payload, merge=True)
        else:
            lock_ref.create(lock_payload)

        try:
            container = _request_graph(
                "POST", f"{ig_user_id}/media",
                {"image_url": image_url, "caption": caption, "access_token": token},
                api_version,
            )
            creation_id = str(container.get("id") or "")
            if not creation_id:
                raise GraphAPIError("Meta did not return a media container ID.")
            lock_ref.set({
                "status": "container_ready",
                "phase": "container_ready",
                "creationId": creation_id,
                "updatedAt": firestore_module.SERVER_TIMESTAMP,
            }, merge=True)
        except Exception as exc:
            lock_ref.set({
                "status": "retryable",
                "phase": "container_create",
                "error": str(exc)[:500],
                "updatedAt": firestore_module.SERVER_TIMESTAMP,
            }, merge=True)
            print(f"Container creation failed before publishing; safe retry remains possible: {exc}")
            return 1

    container_status = _poll_container(creation_id, token, api_version)
    if container_status == "IN_PROGRESS":
        print("Container is still processing; the next five-minute check will resume it.")
        return 0
    if container_status in {"ERROR", "EXPIRED"}:
        lock_ref.set({
            "status": "retryable",
            "phase": "container_create",
            "creationId": "",
            "error": f"Media container status: {container_status}",
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        }, merge=True)
        print(f"Container is {container_status}; it is safe to create a new container on the next check.")
        return 1

    # Write this state before calling media_publish. A crash or network timeout
    # after this point must never automatically submit the same post again.
    lock_ref.set({"status": "publishing", "phase": "publishing",
                  "updatedAt": firestore_module.SERVER_TIMESTAMP}, merge=True)
    try:
        result = _request_graph(
            "POST", f"{ig_user_id}/media_publish",
            {"creation_id": creation_id, "access_token": token},
            api_version,
        )
        media_id = str(result.get("id") or "")
        if not media_id:
            raise GraphAPIError("Meta did not return the published Instagram media ID.")
    except Exception as exc:
        lock_ref.set({
            "status": "uncertain",
            "phase": "publishing",
            "error": str(exc)[:500],
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        }, merge=True)
        _mark_post_failed(
            post_ref,
            "Instagram publish result is uncertain. Check the Instagram account before attempting again.",
            firestore_module,
        )
        print(f"Publish outcome is uncertain; automatic retry disabled to prevent duplicates: {exc}")
        return 1

    # Lock first, then update the post. If the second write fails, the lock still
    # prevents a duplicate publish on the next scheduled run.
    lock_ref.set({
        "status": "published",
        "phase": "published",
        "instagramMediaId": media_id,
        "completedAt": firestore_module.SERVER_TIMESTAMP,
        "updatedAt": firestore_module.SERVER_TIMESTAMP,
    }, merge=True)
    try:
        post_ref.update({
            "status": "published",
            "publishedAt": firestore_module.SERVER_TIMESTAMP,
            "errorMessage": "",
            "updatedAt": firestore_module.SERVER_TIMESTAMP,
        })
    except Exception as exc:
        print(f"WARNING: Instagram published (media ID {media_id}) but Firestore post status update failed ({type(exc).__name__}).")
        return 1

    print(f"SUCCESS: Published Firestore post {post['id']} to Instagram. Media ID: {media_id}")
    return 0


def initialize_firestore() -> tuple[Any, Any]:
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not service_account_json:
        raise SchedulerError("Missing FIREBASE_SERVICE_ACCOUNT_JSON GitHub secret.")
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise SchedulerError("firebase-admin is not installed. Install backend/requirements.txt.") from exc

    try:
        service_account_info = json.loads(service_account_json)
    except json.JSONDecodeError as exc:
        raise SchedulerError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON.") from exc
    project_id = os.getenv("FIREBASE_PROJECT_ID", DEFAULT_PROJECT_ID).strip()
    database_id = os.getenv("FIRESTORE_DATABASE_ID", DEFAULT_DATABASE_ID).strip()
    if not database_id:
        raise SchedulerError("FIRESTORE_DATABASE_ID must not be empty.")
    credential = credentials.Certificate(service_account_info)
    app_name = "mana-tech-firestore-scheduler"
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        app = firebase_admin.initialize_app(credential, {"projectId": project_id}, name=app_name)
    # The web client explicitly selects this named database. Do not silently use
    # Firestore's (default) database, or the worker would see an empty queue.
    return firestore.client(app=app, database_id=database_id), firestore


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the saved Firestore schedule and publish one eligible Instagram post.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect eligibility without changing Firestore or contacting Meta.")
    args = parser.parse_args()

    try:
        db, firestore_module = initialize_firestore()
        return run_scheduler(
            db=db,
            firestore_module=firestore_module,
            token=os.getenv("META_ACCESS_TOKEN", "").strip(),
            api_version=os.getenv("META_API_VERSION", DEFAULT_API_VERSION).strip() or DEFAULT_API_VERSION,
            ig_user_id_override=os.getenv("META_IG_USER_ID", ""),
            required_uid=os.getenv("FIREBASE_OWNER_UID", ""),
            dry_run=args.dry_run or os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes"},
        )
    except SchedulerError as exc:
        print(f"CONFIGURATION / SCHEDULER ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
