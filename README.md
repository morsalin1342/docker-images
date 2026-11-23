# Docker images

The Docker images published as `morsalin1342/<name>` and `easydigital/<name>` on Docker Hub, and the
one file that holds what their repositories say about each other.

<!-- BEGIN GENERATED: related (from catalog.yaml in the morsalin1342/docker-images repository; do not edit by hand) -->
Every image is published under `morsalin1342` (personal) and `easydigital` (organization), from the same build.

| Repository | Images | Description |
|---|---|---|
| [caddy-docker](https://github.com/morsalin1342/caddy-docker) | `morsalin1342/caddy` · `easydigital/caddy` | Standalone Caddy with WAF, rate limiting & caching |
| [frankenphp-docker](https://github.com/morsalin1342/frankenphp-docker) | `morsalin1342/frankenphp` · `easydigital/frankenphp` | Caddy + PHP app server in one container |
| [php-docker](https://github.com/morsalin1342/php-docker) | `morsalin1342/php` · `easydigital/php` | Traditional PHP-FPM & CLI images |
| [nginx-docker](https://github.com/morsalin1342/nginx-docker) | `morsalin1342/nginx` · `easydigital/nginx` | nginx with ModSecurity 3, Brotli, zstd & GeoIP2 |
| [apache-docker](https://github.com/morsalin1342/apache-docker) | `morsalin1342/apache` · `easydigital/apache` | Apache httpd as a static server or php-fpm application server, no PHP inside |
| [adminer-docker](https://github.com/morsalin1342/adminer-docker) | `morsalin1342/adminer` · `easydigital/adminer` | Adminer database tool: the official image plus Alpine security updates |
<!-- END GENERATED: related -->

## What is in this repository

* `catalog.yaml`: the facts the image repositories share. These are project names, the GitHub owner,
  the Docker Hub namespaces, one-line descriptions and Docker Hub short descriptions. Each fact lives
  here once; the repositories do not retype it.
* `sync_docs.py`: fills the generated Related tables in a repository's READMEs from the catalog
  (`--write`), or changes nothing and exits 1 on drift (`--check`). Drift is a stale table, a Docker
  Hub short description or Dockerfile label that disagrees with the catalog, or a README that names a
  namespace or owner the catalog does not know.
* `action.yml`: runs `--check` in a repository's CI. Each image repository calls it from
  `.github/workflows/docs-check.yml`, pinned by commit SHA:

  ```yaml
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
  - uses: morsalin1342/docker-images@<commit SHA> # v1.0.0
  ```

  The pin covers the catalog as well as the script, so a change here reaches a repository only
  through a pull request there.

Each repository's own version pins (httpd, Caddy, Composer, nginx modules) stay in that repository.

## Changing a shared fact

1. Edit `catalog.yaml`, merge it and tag a release (`v1.1.0`).
2. Dependabot opens a pull request in each image repository that moves the pin. Where its check
   fails, run `--write` on that branch and commit the result:

   ```bash
   python3 sync_docs.py --repo caddy-docker --dir ../caddy-docker --write
   ```

The `drift` job in this repository's CI shows which repositories will need that.

A namespace with `publish: false` appears in no README. Switching it to `true` makes every
repository's next `--write` list it.

## Known limits

* The php short description carries "PHP 8.2-8.5" as literal text.
* Whether Docker Hub renders the HTML comments around a generated block invisibly has not been
  checked against a live Hub page.

## License

MIT. See [LICENSE](LICENSE).
