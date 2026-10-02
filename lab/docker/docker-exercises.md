# Docker exercises (weeks 17-20)

1. `docker build --target test app` must pass before `--target runtime` - why is the test stage not in the final image? Check with `docker history lab-api:local`.
2. Compare sizes: build a single-stage `FROM python:3.12` version and compare `docker images`.
3. `docker compose exec web wget -qO- http://db:5432` - fails. Explain using `docker network inspect lab3tier_back`.
4. Kill the db (`docker compose stop db`) and watch `/readyz` return 503 while `/healthz` stays 200. Which one should a load balancer use?
5. Networking: create a `macvlan` network on your VM NIC and give a container a LAN IP. Then try `--network host` and compare `ss -tlnp` on the host.
6. Rootless: install `docker-ce-rootless-extras`, run `dockerd-rootless-setuptool.sh install`, confirm `docker info | grep -i rootless`.
7. Capabilities: `docker run --rm --cap-drop ALL alpine ping 1.1.1.1` fails - add back only `NET_RAW`.
8. seccomp: run with `--security-opt seccomp=unconfined` vs default and try `unshare -r`.
9. CIS benchmark: `docker run --rm --net host --pid host --cap-add audit_control -v /var/lib:/var/lib:ro -v /var/run/docker.sock:/var/run/docker.sock:ro -v /etc:/etc:ro docker/docker-bench-security`
10. Wire `./scan.sh` into the CI workflow in `../cicd` so a HIGH CVE blocks the merge.
