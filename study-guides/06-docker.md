# Phase 6 - Docker: Images, Compose, Networking, Security

**Plan weeks:** 17-20 · **Hours:** 42 · **Lab:** `lab/docker/` (`./lab.sh compose up|scan`), `docker-exercises.md`

| Week | Focus | Deliverable |
|---|---|---|
| 17 | Images, layers, Dockerfile, multi-stage | Optimised multi-stage Dockerfile repo |
| 18 | Compose v2, multi-service, volumes, healthchecks | 3-tier Compose stack |
| 19 | Networking: bridge/overlay/macvlan/host, embedded DNS | Multi-network lab write-up |
| 20 | Rootless, seccomp/AppArmor/caps, Trivy, CIS benchmark | Trivy CI gate + hardened stack |

## How containers actually work
A container is a normal Linux process with: **namespaces** (pid, net, mnt, uts, ipc, user, cgroup - what it can see), **cgroups v2** (how much CPU/mem/IO it can use), **capabilities** (which root powers it keeps), **seccomp** (which syscalls), **LSM** (SELinux/AppArmor labels), and a **union filesystem** (overlay2: read-only image layers + a thin writable layer). Docker = CLI -> dockerd -> containerd -> runc. Kubernetes talks to containerd directly (CRI) - no Docker needed.

## Images and Dockerfiles (week 17)
- Each `RUN/COPY/ADD` creates a layer; order instructions from least to most frequently changing so the cache works (copy `requirements.txt` and install before copying source).
- Multi-stage: build tools stay in the builder stage; runtime stage copies only artefacts. See `lab/docker/app/Dockerfile` (build -> test -> runtime).
- Small bases: `-slim`, `alpine` (musl caveats), distroless, `ubi-minimal`, `scratch` for static Go binaries.
- `CMD` vs `ENTRYPOINT` (exec form `["x","y"]` so signals reach PID 1), `USER 10001`, `HEALTHCHECK`, `.dockerignore`, `ARG` vs `ENV`, BuildKit cache mounts, `docker buildx build --platform linux/amd64,linux/arm64`.
- Tag by immutable identity (git SHA) and deploy by **digest** (`image@sha256:...`); never rely on `latest`.

## Compose (week 18)
`docker compose up -d --build`, `ps`, `logs -f api`, `exec`, `down -v`. `depends_on: condition: service_healthy` + a real healthcheck gives ordered startup. Named volumes for data, bind mounts for dev. `.env` for variables, `profiles:` for optional services, `deploy.resources.limits` for cgroup limits.

## Networking (week 19)
| Driver | Use |
|---|---|
| bridge (user-defined) | default for single host; embedded DNS resolves service names at 127.0.0.11 |
| host | no isolation, container uses host stack (performance, or network tools) |
| none | fully isolated |
| macvlan/ipvlan | container gets its own LAN IP |
| overlay | multi-host (Swarm) - concept maps to K8s CNI overlays |
The default `bridge` network has **no** name resolution; always create your own. `internal: true` networks have no outbound route (see `back` network in the lab compose). Published ports go through iptables/nftables DNAT - and Docker bypasses firewalld/ufw rules by default (know this!).

## Security (week 20)
Checklist you should apply to every image/stack:
- Non-root user; `read_only: true` root fs + `tmpfs` for scratch; `cap_drop: [ALL]` then add only what is needed; `no-new-privileges`.
- Never mount `/var/run/docker.sock` into a container (root on the host). Never `--privileged` without a very good reason.
- Rootless Docker or Podman for dev machines.
- Default seccomp profile blocks ~40+ syscalls (e.g. `mount`, `unshare`-ish ops for non-root). AppArmor `docker-default` on Ubuntu, SELinux `container_t` on RHEL.
- Scan: `trivy image`, `trivy config` (Dockerfile/compose misconfig), `trivy fs --scanners secret`. Gate in CI on fixable HIGH/CRITICAL.
- Secrets: not in `ENV` or image layers (`docker history` shows them); use BuildKit `--secret` at build and Compose/K8s secrets at runtime.
- CIS Docker Benchmark via `docker-bench-security` (command in exercises).

## Interview scenarios (from the 40-scenario PDF, practise answering out loud)
1. Container exits immediately - `docker logs`, `docker inspect --format '{{.State.ExitCode}}'`, check PID 1 command.
2. Image is 1.2 GB - multi-stage, slimmer base, clean package caches in the same layer, `.dockerignore`.
3. Container can't reach another by name - both on the same user-defined network?
4. Disk full on host - `docker system df`, prune images/build cache, log rotation (`max-size` in daemon.json).
5. App works locally, fails in prod image - different base/arch (`--platform`), missing env, read-only fs.

## Self-check
1. Why does changing one line of source rebuild the `pip install` layer in a naive Dockerfile?
2. What does `docker run --cap-drop ALL --cap-add NET_BIND_SERVICE` allow?
3. Difference between `docker stop` and `docker kill`, and why PID 1 matters?
4. Why is a secret passed with `ARG` still leaked?
5. Two ways to make a container unable to reach the internet?

<details><summary>Answers</summary>

1. `COPY . .` came before `RUN pip install`, so the cache is invalidated at that layer.
2. Binding ports < 1024 as non-root, nothing else privileged.
3. stop sends SIGTERM then SIGKILL after 10 s; if PID 1 is a shell that doesn't forward signals the app never sees SIGTERM (use exec form or `--init`).
4. Build args are recorded in image history/metadata.
5. `--network none`, or attach only to an `internal: true` network (or egress firewall).
</details>

## Resources
docker-working-guide.pdf (primary, 29 ch.), 40-docker-scenario-interview-questions.pdf, 5-modern-docker-projects.pdf, https://docs.docker.com/engine/security/, https://labs.play-with-docker.com
