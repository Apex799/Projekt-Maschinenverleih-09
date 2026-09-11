#!/usr/bin/env python3
"""
Erstellt GitHub-Issues aus der Markdown-Datei user_stories.md mithilfe der GitHub CLI (gh).

Voraussetzungen:
  1. GitHub CLI installiert: https://cli.github.com/
  2. Einmalig eingeloggt:      gh auth login
  3. Python 3 vorhanden

Verwendung:
  python3 create_github_issues.py user_stories.md --repo <owner>/<repo>

  Optional (Trockenlauf ohne tatsächliches Anlegen, nur Ausgabe):
  python3 create_github_issues.py user_stories.md --repo <owner>/<repo> --dry-run

Das Skript:
  - liest die Markdown-Datei ein
  - trennt sie an den Abschnitten, die mit "## " beginnen (= eine User Story/ein Issue)
  - extrahiert Titel, Beschreibungstext und die in "**Labels:** `a`, `b`" angegebenen Labels
  - legt fehlende Labels im Repository an (falls noch nicht vorhanden)
  - erstellt für jede User Story ein GitHub-Issue per `gh issue create`
"""

import argparse
import re
import subprocess
import sys


def parse_markdown(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Jeder Issue-Block beginnt mit einer Zeile "## <Nummer>. <Titel>"
    blocks = re.split(r"\n(?=## \d+\.\s)", content)
    issues = []

    for block in blocks:
        block = block.strip()
        if not block.startswith("## "):
            continue  # z. B. der Einleitungstext vor der ersten Story

        # Titel extrahieren und aus dem Block entfernen
        title_match = re.match(r"## \d+\.\s*(.+)", block)
        title = title_match.group(1).strip()
        body = block[title_match.end():].strip()

        # Trennlinie "---" am Ende des Blocks entfernen, falls vorhanden
        body = re.sub(r"\n?-{3,}\s*$", "", body).strip()

        # Labels-Zeile extrahieren, z. B.: **Labels:** `user-story`, `lernfeld-LF9`
        labels = []
        labels_match = re.search(r"\*\*Labels:\*\*\s*(.+)", body)
        if labels_match:
            labels = [l.strip().strip("`") for l in labels_match.group(1).split(",")]
            # Labels-Zeile aus dem Body entfernen, sie steht bereits als GitHub-Label am Issue
            body = body[: labels_match.start()].strip()

        issues.append({"title": title, "body": body, "labels": labels})

    return issues


def ensure_labels_exist(repo, labels, dry_run):
    for label in labels:
        cmd = ["gh", "label", "create", label, "--repo", repo, "--color", "ededed", "--force"]
        if dry_run:
            print(f"[dry-run] {' '.join(cmd)}")
            continue
        subprocess.run(cmd, capture_output=True, text=True)  # Fehler ignorieren, falls Label existiert


def create_issue(repo, issue, dry_run):
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", issue["title"], "--body", issue["body"]]
    for label in issue["labels"]:
        cmd += ["--label", label]

    if dry_run:
        print(f"[dry-run] gh issue create --repo {repo} --title \"{issue['title']}\" "
              f"--label {','.join(issue['labels'])}")
        return

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✔ Issue erstellt: {issue['title']} -> {result.stdout.strip()}")
    else:
        print(f"✘ Fehler bei '{issue['title']}': {result.stderr.strip()}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="User Stories aus Markdown als GitHub-Issues anlegen")
    parser.add_argument("markdown_file", help="Pfad zur user_stories.md")
    parser.add_argument("--repo", required=True, help="Ziel-Repository im Format owner/repo")
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts anlegen")
    args = parser.parse_args()

    issues = parse_markdown(args.markdown_file)
    print(f"{len(issues)} User Stories gefunden.\n")

    all_labels = sorted({label for issue in issues for label in issue["labels"]})
    print(f"Lege/prüfe {len(all_labels)} Labels an: {', '.join(all_labels)}\n")
    ensure_labels_exist(args.repo, all_labels, args.dry_run)

    for issue in issues:
        create_issue(args.repo, issue, args.dry_run)


if __name__ == "__main__":
    main()
