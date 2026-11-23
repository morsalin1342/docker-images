#!/usr/bin/env python3
"""Keep a sibling repository's shared facts in step with catalog.yaml.

    sync_docs.py --catalog catalog.yaml --repo caddy-docker --dir . --write
    sync_docs.py --catalog catalog.yaml --repo caddy-docker --dir . --check

--write rewrites the generated blocks in the repository's READMEs.
--check rewrites nothing and exits 1 on any drift:

  * a generated block differs from what the catalog produces;
  * a Docker Hub short description in the workflow differs from hub_short;
  * the Dockerfile's image title or source label differs from the catalog;
  * a README names a Docker Hub namespace, or a GitHub owner for a sibling
    repository, that the catalog does not know.

A generated block sits between these markers; everything outside them is the
repository's own prose and is never touched:

    <!-- BEGIN GENERATED: related -->
    <!-- END GENERATED: related -->
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

BEGIN = "<!-- BEGIN GENERATED: related (from catalog.yaml in the morsalin1342/docker-images repository; do not edit by hand) -->"
END = "<!-- END GENERATED: related -->"
BLOCK = re.compile(r"<!-- BEGIN GENERATED: related[^>]*-->.*?<!-- END GENERATED: related -->", re.S)


def load(path):
    m = yaml.safe_load(Path(path).read_text())
    if m.get("version") != 1:
        sys.exit(f"{path}: unsupported catalog version {m.get('version')!r}")
    return m


def live(m):
    """Projects that exist. A project with status: planned is in the catalog but in no README yet."""
    return [(k, p) for k, p in m["projects"].items() if p.get("status") != "planned"]


def published(m):
    return [(k, v) for k, v in m["namespaces"].items() if v.get("publish")]


def owner_of(m, project):
    return project.get("owner", m["source_owner"])


def gh_url(m, project):
    return f"https://github.com/{owner_of(m, project)}/{project['repo']}"


def images_cell(m, project):
    if project["kind"] != "image":
        return "—"
    key = project_key(m, project)
    refs = [f"`{v['hub']}/{key}`" for _, v in published(m)]
    if m.get("ghcr_owner"):
        refs.append(f"`ghcr.io/{m['ghcr_owner']}/{key}`")
    return " · ".join(refs)


def where_published(m):
    """The intro sentence: every registry an image goes to."""
    places = [f"Docker Hub as `{v['hub']}/<image>`" for _, v in published(m)]
    if m.get("ghcr_owner"):
        places.append(f"GitHub Container Registry as `ghcr.io/{m['ghcr_owner']}/<image>`")
    return " and to ".join(places)


def project_key(m, project):
    return next(k for k, v in m["projects"].items() if v is project)


def render_github(m, key):
    """The table in a repository's own README: every project, every live namespace.

    key is None for the catalog's own README, which lists every project."""
    over = m.get("related", {}).get(key, {})
    include = over.get("include")
    descs = over.get("descriptions", {})
    out = []
    out.append(over.get("intro") or f"Every image is published to {where_published(m)}, from the same build.")
    out.append("")
    out.append("| Repository | Images | Description |")
    out.append("|---|---|---|")
    for k, p in live(m):
        if k == key:
            continue
        if include is not None and k not in include:
            continue
        if include is None and p["kind"] == "plugin" and key is not None and key not in p.get("related_from", []):
            continue
        out.append(f"| [{p['repo']}]({gh_url(m, p)}) | {images_cell(m, p)} | {descs.get(k, p['description'])} |")
    if over.get("also"):
        links = [f"[{m['projects'][a]['repo']}]({gh_url(m, m['projects'][a])})" for a in over["also"]]
        if len(links) > 1:
            links = [", ".join(links[:-1]) + " and " + links[-1]]
        out.append("")
        out.append(f"{over['also_intro']} {links[0]}.")
    return "\n".join(out)


def render_hub(m, key, ns):
    """The table in a Docker Hub README: siblings in this namespace, then this image elsewhere."""
    me = m["projects"][key]
    hub = m["namespaces"][ns]["hub"]
    out = ["| Image / Tool | Description |", "|--------------|-------------|"]
    for k, p in live(m):
        if k == key:
            continue
        if p["kind"] == "image":
            out.append(f"| [{hub}/{k}](https://hub.docker.com/r/{hub}/{k}) | {p['description']} |")
        elif key in p.get("related_from", []):
            out.append(f"| [{p['repo']}]({gh_url(m, p)}) | {p['description']} |")
    if me["kind"] == "image":
        for n, v in published(m):
            if n != ns:
                out.append(f"| [{v['hub']}/{key}](https://hub.docker.com/r/{v['hub']}/{key}) | Same image, {v['label']} namespace |")
        if m.get("ghcr_owner"):
            out.append(f"| [ghcr.io/{m['ghcr_owner']}/{key}]({gh_url(m, me)}/pkgs/container/{key}) | Same image, GitHub Container Registry |")
    return "\n".join(out)


def expected_blocks(m, key, root):
    """{path: block text} for every README of this repository that carries a block."""
    res = {}
    readme = root / "README.md"
    if readme.exists():
        res[readme] = render_github(m, key)
    if key is not None and m["projects"][key]["kind"] == "image":
        for ns, v in published(m):
            f = root / v["hub_readme"]
            if f.exists():
                res[f] = render_hub(m, key, ns)
    return res


def wrap(body):
    return f"{BEGIN}\n{body}\n{END}"


def check_files(m, key, root, write):
    problems = []
    for path, body in expected_blocks(m, key, root).items():
        text = path.read_text()
        if not BLOCK.search(text):
            problems.append(f"{path.name}: no generated block (add the BEGIN/END markers where the Related table belongs)")
            continue
        new = BLOCK.sub(lambda _: wrap(body), text, count=1)
        if new != text:
            if write:
                path.write_text(new)
                print(f"updated {path.name}")
            else:
                problems.append(f"{path.name}: generated block is out of date; run sync_docs.py --write")
    return problems


def check_workflow(m, key, root):
    p = m["projects"][key]
    f = root / ".github/workflows/docker-publish.yml"
    if p["kind"] != "image" or not f.exists() or "hub_short" not in p:
        return []
    wf = yaml.safe_load(f.read_text())
    got = []
    for job in wf.get("jobs", {}).values():
        for step in job.get("steps", []):
            w = step.get("with") or {}
            if "short-description" in w:
                got.append(w["short-description"])
    if not got:
        return [f"{f.name}: no Docker Hub short-description found"]
    return [f"{f.name}: short-description {s!r} differs from the catalog's hub_short" for s in got if s != p["hub_short"]]


def check_dockerfile(m, key, root):
    p = m["projects"][key]
    f = root / "Dockerfile"
    if p["kind"] != "image" or not f.exists():
        return []
    t = f.read_text()
    bad = []
    src = re.search(r'org\.opencontainers\.image\.source="([^"]*)"', t)
    if not src or src.group(1) != gh_url(m, p):
        bad.append(f"Dockerfile: image.source label is {src.group(1) if src else 'missing'}, expected {gh_url(m, p)}")
    title = re.search(r'org\.opencontainers\.image\.title="([^"]*)"', t)
    if not title or title.group(1) != key:
        bad.append(f"Dockerfile: image.title label is {title.group(1) if title else 'missing'}, expected {key}")
    return bad


def check_names(m, key, root):
    """Namespaces and owners a README mentions must be ones the catalog knows."""
    known_hub = {v["hub"] for v in m["namespaces"].values()}
    repos = {p["repo"]: owner_of(m, p) for p in m["projects"].values()}
    bad = []
    for f in sorted(root.glob("README*.md")):
        t = f.read_text()
        for ns in set(re.findall(r"hub\.docker\.com/(?:r|u)/([A-Za-z0-9_.-]+)", t)):
            if ns not in known_hub:
                bad.append(f"{f.name}: Docker Hub namespace {ns!r} is not in the catalog")
        for owner in set(re.findall(r"ghcr\.io/([A-Za-z0-9_.-]+)/", t)):
            if owner != m.get("ghcr_owner"):
                bad.append(f"{f.name}: GitHub Container Registry owner {owner!r} is not the catalog's ghcr_owner")
        for owner, repo in set(re.findall(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", t)):
            if repo in repos and owner != repos[repo]:
                bad.append(f"{f.name}: {owner}/{repo} should be {repos[repo]}/{repo}")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(Path(__file__).with_name("catalog.yaml")), help="default: catalog.yaml next to this script")
    ap.add_argument("--repo", required=True, help="repository name, e.g. caddy-docker")
    ap.add_argument("--dir", default=".")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    a = ap.parse_args()

    m = load(a.catalog)
    # The catalog's own repository has no project entry; its README lists every project.
    if a.repo == m.get("catalog_repo"):
        key = None
    else:
        key = next((k for k, p in m["projects"].items() if p["repo"] == a.repo), None)
        if key is None:
            sys.exit(f"{a.repo}: not a project in the catalog")
    root = Path(a.dir)

    problems = check_files(m, key, root, a.write)
    if a.check:
        if key is not None:
            problems += check_workflow(m, key, root) + check_dockerfile(m, key, root)
        problems += check_names(m, key, root)
    for p in problems:
        print(f"::error::{p}" if a.check else p)
    if problems:
        sys.exit(1)
    print(f"{a.repo}: consistent with the catalog" if a.check else f"{a.repo}: done")


if __name__ == "__main__":
    main()
