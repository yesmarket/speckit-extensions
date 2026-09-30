#!/usr/bin/env python3
"""Deterministic helpers for the rationalisation phase of constitution-from-confluence.

Standard library only. The model makes the keep / adapt / drop judgements; this script does
the parts that must be exact: splitting pages into rule units, hashing them, comparing with the
lock file, and writing the audit table, the rationalised sources and the lock decisions.

Subcommands
  extract <source.md>...                  Split source files into rule units (JSON on stdout).
  diff    --rules R --lock LOCK [--audit A] [--grounding-changed] [--notes-changed]
                                          Which decisions can be reused and which need a decision.
                                          --grounding-changed re-opens dropped and adapted rules.
                                          --notes-changed re-opens every rule. Decisions that were
                                          edited by hand (pinned with "o": true) are never re-opened
                                          by either flag, only by a change to the rule's own text.
  summary --rules R --decisions D [--lock LOCK]
                                          Counts, drops, and the MAJOR-bump signal (JSON).
  audit   --rules R --decisions D         Markdown audit table (stdout).
  emit    --rules R --decisions D --out-dir DIR
                                          Write the kept and adapted units, one file per page.
  lock    --rules R --decisions D --lock LOCK
                                          Rewrite the `rationalisation:` block of the lock file.

Source files have the header written by the skill (id, title, url, version, labels between two
`---` lines) followed by the page body in markdown. File names are `<pageId>-<slug>.md`.
"""
import argparse
import hashlib
import json
import os
import re
import sys

NORMATIVE = re.compile(r"\b(MUST NOT|MUST|SHOULD NOT|SHOULD|MAY)\b")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUM_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$")
RULE_START = re.compile(r"^\s*[-*]\s+\*\*(\d+(?:\.\d+)*)(?=[\s.*])")
FENCE = re.compile(r"^\s*```")
HEADER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
DECISIONS = ("keep", "adapt", "drop")


# ---------------------------------------------------------------- helpers

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def normalise(text):
    """Text used for hashing: markup and whitespace changes are not material changes."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def digest(text):
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()[:10]


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parse_source(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    meta, body = {}, text
    match = HEADER.match(text)
    if match:
        for line in match.group(1).splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
        body = text[match.end():]
    stem = os.path.basename(path)
    stem = stem[:-3] if stem.endswith(".md") else stem
    page_id, _, slug = stem.partition("-")
    meta.setdefault("id", page_id)
    return meta, (slug or page_id), body


# ---------------------------------------------------------------- extract

def split_sections(lines):
    """Split into (level, heading, body_lines). Text before the first heading is metadata."""
    sections, current, in_fence = [], None, False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
        heading = None if in_fence else HEADING.match(line)
        if heading and not FENCE.match(line):
            current = {"level": len(heading.group(1)), "heading": heading.group(2), "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    return sections


def split_rules(lines):
    """Return (rules, remainder_lines). A rule is a list item that starts with a bold number."""
    rules, remainder, i, n, in_fence = [], [], 0, len(lines), False
    while i < n:
        line = lines[i]
        if FENCE.match(line):
            in_fence = not in_fence
        start = None if in_fence else RULE_START.match(line)
        if not start:
            remainder.append(line)
            i += 1
            continue
        j = i + 1
        while j < n:
            nxt = lines[j]
            if FENCE.match(nxt) and not nxt.startswith(" "):
                break
            if RULE_START.match(nxt):
                break
            if nxt.strip() == "":
                k = j + 1
                while k < n and lines[k].strip() == "":
                    k += 1
                if k >= n or not lines[k].startswith(" "):
                    break
            elif not nxt.startswith(" ") and re.match(r"^(#|\||- |\* |\d+\. )", nxt):
                break
            j += 1
        rules.append((start.group(1), "\n".join(lines[i:j]).rstrip()))
        i = j
    return rules, remainder


def strip_fences(lines):
    kept, in_fence = [], False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return kept


def extract(paths):
    out = {"pages": {}, "rules": [], "context": []}
    seen = set()

    def add(slug, meta, uid, number, heading, kind, text):
        base = uid
        count = 2
        while uid in seen:
            uid = "%s~%d" % (base, count)
            count += 1
        seen.add(uid)
        out["rules"].append({
            "id": uid, "page": meta["id"], "slug": slug, "title": meta.get("title", slug),
            "number": number, "heading": heading, "kind": kind,
            "hash": digest(text), "text": text,
        })

    for path in paths:
        meta, slug, body = parse_source(path)
        out["pages"][slug] = meta
        for section in split_sections(body.split("\n")):
            heading = section["heading"]
            numbered = NUM_HEADING.match(heading)
            section_key = numbered.group(1) if numbered else (slugify(heading) or "section")
            rules, remainder = split_rules(section["lines"])
            remainder_text = "\n".join(remainder).strip()
            if rules:
                for number, text in rules:
                    add(slug, meta, "%s:%s" % (slug, number), number, heading, "rule", text)
                if remainder_text:
                    if NORMATIVE.search("\n".join(strip_fences(remainder))):
                        add(slug, meta, "%s:%s.other" % (slug, section_key), section_key,
                            heading, "other", remainder_text)
                    else:
                        out["context"].append({"slug": slug, "heading": heading, "text": remainder_text})
            elif remainder_text:
                add(slug, meta, "%s:%s" % (slug, section_key), section_key, heading, "section", remainder_text)
    return out


# ---------------------------------------------------------------- lock and audit parsing

DECISION_LINE = re.compile(r"^\s+-\s+(\{.*\})\s*$")
AUDIT_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|[^|]*\|\s*(keep|adapt|drop)\s*\|")


def lock_decisions(path):
    decisions = {}
    if not path or not os.path.exists(path):
        return decisions
    in_block = False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if re.match(r"^rationalisation:", line):
                in_block = True
                continue
            if in_block and line.strip() and not line.startswith(" "):
                in_block = False
            match = DECISION_LINE.match(line) if in_block else None
            if match:
                try:
                    item = json.loads(match.group(1))
                    decisions[item["id"]] = {"d": item["d"], "h": item["h"], "o": bool(item.get("o"))}
                except (ValueError, KeyError):
                    continue
    return decisions


def audit_decisions(path):
    found = {}
    if not path or not os.path.exists(path):
        return found
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            match = AUDIT_ROW.match(line)
            if match:
                found[match.group(1)] = match.group(2)
    return found


def cmd_diff(args):
    rules = load_json(args.rules)["rules"]
    previous = lock_decisions(args.lock)
    audit = audit_decisions(args.audit)
    current = {r["id"]: r["hash"] for r in rules}
    result = {"reuse": {}, "needs_decision": [], "removed": [], "overrides": [], "override_ids": []}
    for rule_id, rule_hash in current.items():
        prev = previous.get(rule_id)
        if prev is None:
            result["needs_decision"].append({"id": rule_id, "why": "new"})
        elif prev["h"] != rule_hash:
            result["needs_decision"].append({"id": rule_id, "why": "changed", "previous": prev["d"]})
        else:
            decision, pinned = prev["d"], prev["o"]
            if rule_id in audit and audit[rule_id] != decision:
                result["overrides"].append({"id": rule_id, "from": decision, "to": audit[rule_id]})
                decision, pinned = audit[rule_id], True
            if pinned:
                result["override_ids"].append(rule_id)
                result["reuse"][rule_id] = decision
            elif args.notes_changed:
                result["needs_decision"].append(
                    {"id": rule_id, "why": "notes-changed", "previous": decision})
            elif args.grounding_changed and decision in ("drop", "adapt"):
                result["needs_decision"].append(
                    {"id": rule_id, "why": "grounding-changed", "previous": decision})
            else:
                result["reuse"][rule_id] = decision
    result["removed"] = sorted(set(previous) - set(current))
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------- decisions

def load_decisions(rules, path):
    decisions = load_json(path)
    missing = [r["id"] for r in rules if r["id"] not in decisions]
    invalid = [k for k, v in decisions.items() if v.get("decision") not in DECISIONS]
    if missing or invalid:
        sys.exit("ERROR: every rule needs a decision (keep|adapt|drop).\n  missing: %s\n  invalid: %s"
                 % (missing[:20], invalid[:20]))
    return decisions


def cmd_summary(args):
    rules = load_json(args.rules)["rules"]
    decisions = load_decisions(rules, args.decisions)
    previous = lock_decisions(args.lock)
    counts = {d: 0 for d in DECISIONS}
    by_page = {}
    for r in rules:
        d = decisions[r["id"]]["decision"]
        counts[d] += 1
        by_page.setdefault(r["title"], {x: 0 for x in DECISIONS})[d] += 1
    dropped = [r["id"] for r in rules if decisions[r["id"]]["decision"] == "drop"]
    newly_dropped = [i for i in dropped if previous.get(i, {}).get("d") != "drop"]
    lost = [i for i in newly_dropped if previous.get(i, {}).get("d") in ("keep", "adapt")]
    lost += [i for i, p in previous.items()
             if i not in {r["id"] for r in rules} and p["d"] in ("keep", "adapt")]
    print(json.dumps({
        "counts": counts, "by_page": by_page, "dropped": dropped,
        "newly_dropped": newly_dropped,
        "previously_present_now_removed": lost,
        "major_bump": bool(lost),
    }, indent=2))


def cmd_audit(args):
    rules = load_json(args.rules)["rules"]
    decisions = load_decisions(rules, args.decisions)
    print("| Rule | Source page | Decision | Reason |")
    print("|---|---|---|---|")
    for r in rules:
        d = decisions[r["id"]]
        reason = d.get("reason", "").replace("|", "\\|").replace("\n", " ")
        if d["decision"] == "adapt" and d.get("adaptation"):
            reason += " Adaptation: " + d["adaptation"].replace("|", "\\|").replace("\n", " ")
        print("| `%s` | %s | %s | %s |" % (r["id"], r["title"], d["decision"], reason.strip()))


def cmd_emit(args):
    data = load_json(args.rules)
    rules = data["rules"]
    decisions = load_decisions(rules, args.decisions)
    os.makedirs(args.out_dir, exist_ok=True)
    kept_headings = {}
    for r in rules:
        if decisions[r["id"]]["decision"] in ("keep", "adapt"):
            kept_headings.setdefault(r["slug"], set()).add(r["heading"])
    written = []
    for slug, meta in data["pages"].items():
        if slug not in kept_headings:
            continue
        lines = ["---"]
        for key in ("id", "title", "url", "version", "labels"):
            if key in meta:
                value = meta[key]
                lines.append('%s: %s' % (key, value if key in ("version", "labels") else '"%s"' % value))
        lines += ["rationalised: true", "---", "# %s (rationalised)" % meta.get("title", slug), ""]
        heading = None
        for r in [x for x in rules if x["slug"] == slug]:
            d = decisions[r["id"]]
            if d["decision"] == "drop":
                continue
            if r["heading"] != heading:
                if heading is not None:
                    for c in [c for c in data["context"] if c["slug"] == slug and c["heading"] == heading]:
                        lines += [c["text"], ""]
                heading = r["heading"]
                lines += ["## " + heading, ""]
            lines += [r["text"], ""]
            if d["decision"] == "adapt" and d.get("adaptation"):
                lines += ["> Adaptation (%s): %s" % (r["id"], d["adaptation"].strip()), ""]
        if heading is not None:
            for c in [c for c in data["context"] if c["slug"] == slug and c["heading"] == heading]:
                lines += [c["text"], ""]
        path = os.path.join(args.out_dir, "%s-%s.rationalised.md" % (meta["id"], slug))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines).rstrip() + "\n")
        written.append(path)
    print(json.dumps({"files": written}, indent=2))


def cmd_lock(args):
    rules = load_json(args.rules)["rules"]
    decisions = load_decisions(rules, args.decisions)
    block = ["rationalisation:", "  decisions:"]
    for r in rules:
        entry = {"id": r["id"], "d": decisions[r["id"]]["decision"], "h": r["hash"]}
        if decisions[r["id"]].get("override"):
            entry["o"] = True
        block.append("    - %s" % json.dumps(entry, ensure_ascii=False))
    lines = []
    if os.path.exists(args.lock):
        with open(args.lock, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("rationalisation:")), None)
    if start is None:
        lines += block
    else:
        end = start + 1
        while end < len(lines) and (not lines[end].strip() or lines[end].startswith((" ", "#"))):
            end += 1
        lines[start:end] = block
    with open(args.lock, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines).rstrip() + "\n")
    print("wrote %d decisions to %s" % (len(rules), args.lock))


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract"); p.add_argument("files", nargs="+")
    for name in ("diff", "summary", "audit", "emit", "lock"):
        p = sub.add_parser(name)
        p.add_argument("--rules", required=True)
        if name != "diff":
            p.add_argument("--decisions", required=True)
        if name in ("diff", "summary", "lock"):
            p.add_argument("--lock", required=(name != "summary"))
        if name == "diff":
            p.add_argument("--audit")
            p.add_argument("--grounding-changed", action="store_true")
            p.add_argument("--notes-changed", action="store_true")
        if name == "emit":
            p.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    if args.cmd == "extract":
        print(json.dumps(extract(args.files), indent=2, ensure_ascii=False))
    else:
        {"diff": cmd_diff, "summary": cmd_summary, "audit": cmd_audit,
         "emit": cmd_emit, "lock": cmd_lock}[args.cmd](args)


if __name__ == "__main__":
    main()
