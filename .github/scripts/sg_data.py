"""Collect public GitHub data for the Steins;Gate profile graphs (stdlib only)."""
import datetime as dt, json, os, re, sys, urllib.request
from collections import Counter

API = "https://api.github.com"
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def _get(url, token=None, accept="application/vnd.github+json"):
    h = {"User-Agent": "sg-graph", "Accept": accept}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30).read()


def calendar(user, token):
    if token:
        try:
            q = ("query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{"
                 "totalContributions weeks{contributionDays{date weekday contributionCount contributionLevel}}}}}}")
            req = urllib.request.Request(f"{API}/graphql", data=json.dumps({"query": q, "variables": {"login": user}}).encode(),
                                         headers={"Authorization": f"bearer {token}", "User-Agent": "sg-graph"})
            data = json.load(urllib.request.urlopen(req, timeout=30))
            weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            return [dict(x=x, y=d["weekday"], date=d["date"], count=d["contributionCount"],
                         level=LEVELS[d["contributionLevel"]]) for x, w in enumerate(weeks) for d in w["contributionDays"]]
        except Exception as e:  # noqa: BLE001
            print(f"GraphQL failed ({e}); using public page", file=sys.stderr)
    html = _get(f"https://github.com/users/{user}/contributions", accept="text/html").decode()
    tips = {m.group(1): m.group(2) for m in re.finditer(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)', html)}
    out = []
    for dt_, wd, w, lv in re.findall(r'data-date="([\d-]+)" id="contribution-day-component-(\d+)-(\d+)" data-level="(\d)"', html):
        tip = tips.get(f"contribution-day-component-{wd}-{w}", "")
        m = re.match(r"(\d+) contribution", tip)
        out.append(dict(x=int(w), y=int(wd), date=dt_, count=int(m.group(1)) if m else 0, level=int(lv)))
    return out


def streaks(cells):
    days = sorted(cells, key=lambda c: c["date"])
    longest = cur = 0
    for c in days:
        cur = cur + 1 if c["count"] > 0 else 0
        longest = max(longest, cur)
    # current streak: allow today to be empty
    current = 0
    for c in reversed(days[:-1] if days and days[-1]["count"] == 0 else days):
        if c["count"] > 0:
            current += 1
        else:
            break
    return longest, current


def verify_public(repo, token):
    """True only if the repos API confirms a public repo. Any error -> False."""
    try:
        info = json.loads(_get(f"{API}/repos/{repo}", token))
    except Exception:  # noqa: BLE001
        return False
    return (info.get("private") is False and info.get("visibility", "public") == "public"
            and info.get("full_name", "").lower() == repo.lower())


def current_experiment(user, own, token):
    """Most recently pushed public repo (profile repos excluded)."""
    skip = {user.lower(), "profile-readme-test"}
    for r in sorted(own, key=lambda r: r.get("pushed_at") or "", reverse=True):
        name, desc = r.get("name") or "", r.get("description") or ""
        if r.get("private") is not False or r.get("fork") or name.lower() in skip:
            continue
        if verify_public(f"{user}/{name}", token):
            return dict(name=name, description=desc, pushed_at=r.get("pushed_at"))
    return None


def pinned_repos(user, token):
    """Pinned repo names via GraphQL (needs a token). Empty list on any problem."""
    if not token:
        return []
    q = ("query($login:String!){user(login:$login){pinnedItems(first:6,types:REPOSITORY){nodes{"
         "... on Repository{name isPrivate isFork owner{login}}}}}}")
    try:
        req = urllib.request.Request(f"{API}/graphql", data=json.dumps({"query": q, "variables": {"login": user}}).encode(),
                                     headers={"Authorization": f"bearer {token}", "User-Agent": "sg-graph"})
        nodes = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["pinnedItems"]["nodes"]
    except Exception as e:  # noqa: BLE001
        print(f"pinned items unavailable ({e})", file=sys.stderr)
        return []
    return [n["name"] for n in nodes if n and n.get("isPrivate") is False and not n.get("isFork")
            and (n.get("owner") or {}).get("login", "").lower() == user.lower()]


def gadgets(user, own, token, limit=6, pinned=None):
    """Pinned repos first, then the rest by score (stars + recent activity). Public, non-fork, no profile repos."""
    skip = {user.lower(), "profile-readme-test"}
    now = dt.datetime.now(dt.timezone.utc)
    by_name = {r["name"]: r for r in own}
    pinned = pinned if pinned is not None else pinned_repos(user, token)

    def age(r):
        try:
            return (now - dt.datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00"))).days
        except Exception:  # noqa: BLE001
            return 9999

    def score(r):
        a = age(r)
        return (r.get("stargazers_count", 0) * 2 + (6 if a <= 30 else 3 if a <= 90 else 1 if a <= 365 else 0), r.get("pushed_at") or "")

    rest = sorted((r for r in own if r["name"] not in pinned), key=score, reverse=True)
    order = [by_name[n] for n in pinned if n in by_name] + rest
    out = []
    for r in order:
        if len(out) >= limit:
            break
        name = r.get("name") or ""
        if r.get("private") is not False or r.get("fork") or name.lower() in skip:
            continue
        if not verify_public(f"{user}/{name}", token):
            continue
        out.append(dict(name=name, description=r.get("description") or "", language=r.get("language") or "",
                        stars=r.get("stargazers_count", 0), pushed=(r.get("pushed_at") or "")[:10], age=age(r),
                        pinned=name in pinned))
    return out


def build_feed(user, events, own, token, tz, limit=6):
    """Latest pushes only, from repos verified public. Anything doubtful is skipped."""
    checked = {}

    def public_repo(repo):
        if repo not in checked:
            checked[repo] = verify_public(repo, token)
        return checked[repo]

    def first_line(m, n=78):
        m = (m or "").strip().split("\n")[0].strip()
        return m if len(m) <= n else m[: n - 1].rstrip() + "\u2026"

    out = []
    for e in sorted(events, key=lambda e: e.get("created_at", ""), reverse=True):
        if len(out) >= limit:
            break
        if e.get("type") != "PushEvent" or e.get("public") is not True:
            continue
        repo, p = (e.get("repo") or {}).get("name", ""), e.get("payload") or {}
        if not repo or repo.split("/")[-1].lower() in {user.lower(), "profile-readme-test"}:
            continue  # never list the profile repos themselves
        if not public_repo(repo):
            continue
        short = repo.split("/", 1)[1] if repo.lower().startswith(user.lower() + "/") else repo
        n, msg = 0, ""
        try:
            cmp_ = json.loads(_get(f"{API}/repos/{repo}/compare/{p['before']}...{p['head']}", token))
            n = cmp_.get("total_commits") or len(cmp_.get("commits", []))
            if cmp_.get("commits"):
                msg = cmp_["commits"][-1]["commit"]["message"]
        except Exception:  # noqa: BLE001
            try:
                msg = json.loads(_get(f"{API}/repos/{repo}/commits/{p.get('head')}", token))["commit"]["message"]
            except Exception:  # noqa: BLE001
                pass
        n = n or p.get("size") or 1
        if out and out[-1]["repo"] == repo:
            out[-1]["n"] += n
            out[-1]["head"] = f"pushed {out[-1]['n']} commits to {short}"
            continue
        t = dt.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).astimezone(tz)
        out.append(dict(kind="push", n=n, repo=repo, time=t.strftime("%Y-%m-%d %H:%M"),
                        head=f"pushed {n} commit{'s' if n != 1 else ''} to {short}", body=first_line(msg)))
    return out


def collect(user, token=None):
    cells = calendar(user, token)
    u = json.loads(_get(f"{API}/users/{user}", token))
    repos = json.loads(_get(f"{API}/users/{user}/repos?per_page=100&type=owner&sort=pushed", token))
    own = [r for r in repos if not r.get("fork")]
    langs = Counter()
    for r in own:
        try:
            for k, v in json.loads(_get(r["languages_url"], token)).items():
                langs[k] += v
        except Exception as e:  # noqa: BLE001
            print(f"languages for {r['name']} failed: {e}", file=sys.stderr)
    events = []
    for page in (1, 2, 3):
        try:
            batch = json.loads(_get(f"{API}/users/{user}/events/public?per_page=100&page={page}", token))
        except Exception:  # noqa: BLE001
            break
        events += batch
        if len(batch) < 100:
            break
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(os.environ.get("SG_TZ", "Europe/Berlin"))
    except Exception:  # noqa: BLE001
        tz = dt.timezone.utc
    hours, wdays = [0] * 24, [0] * 7
    kinds = Counter()
    for e in events:
        t = dt.datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).astimezone(tz)
        kinds[e["type"]] += 1
        if e["type"] == "PushEvent":
            n = e.get("payload", {}).get("size") or 1
            hours[t.hour] += n
            wdays[t.weekday()] += n
    # commit timestamps from his own public repos (last year) -> time-of-day / weekday histogram
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    c_hours, c_wdays, n_commits = [0] * 24, [0] * 7, 0
    for r in own:
        for page in (1, 2, 3):
            try:
                batch = json.loads(_get(f"{API}/repos/{user}/{r['name']}/commits?author={user}&since={since}&per_page=100&page={page}", token))
            except Exception:  # noqa: BLE001
                break
            for c in batch:
                d = (c.get("commit") or {}).get("author", {}).get("date")
                if not d:
                    continue
                t = dt.datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(tz)
                c_hours[t.hour] += 1
                c_wdays[t.weekday()] += 1
                n_commits += 1
            if len(batch) < 100:
                break
    if n_commits:
        hours, wdays = c_hours, c_wdays
    feed = build_feed(user, events, own, token, tz)
    longest, current = streaks(cells)
    return dict(
        user=user, cells=cells,
        total=sum(c["count"] for c in cells),
        active_days=sum(1 for c in cells if c["count"] > 0),
        longest_streak=longest, current_streak=current,
        best_day=max(cells, key=lambda c: c["count"]) if cells else None,
        public_repos=u.get("public_repos", 0), followers=u.get("followers", 0), following=u.get("following", 0),
        created_at=u.get("created_at", ""),
        stars=sum(r.get("stargazers_count", 0) for r in own),
        languages=langs.most_common(),
        repos=[dict(name=r["name"], stars=r["stargazers_count"], language=r.get("language"), pushed_at=r["pushed_at"]) for r in own],
        push_hours=hours, push_weekdays=wdays, commits_year=n_commits, event_kinds=kinds.most_common(),
        events_seen=len(events), feed=feed, user_id=u.get("id"),
        experiment=current_experiment(user, own, token), gadgets=gadgets(user, own, token),
        generated=dt.datetime.now(tz).strftime("%Y-%m-%d %H:%M"),
    )


if __name__ == "__main__":
    d = collect(sys.argv[1] if len(sys.argv) > 1 else "yubinex", os.environ.get("GITHUB_TOKEN"))
    json.dump(d, open(sys.argv[2] if len(sys.argv) > 2 else "data.json", "w"), indent=1)
    print({k: v for k, v in d.items() if k not in ("cells", "repos")})
