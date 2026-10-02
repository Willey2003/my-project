# Hubble exercises (CCA: Network Observability 10%, plus a lot of Architecture and Policy questions)

Setup once per shell (from `lab/golden/cilium/`, after `./up.sh`):
```bash
cilium hubble port-forward &          # relay -> localhost:4245
hubble status                         # "Healthcheck (via localhost:4245): Ok", flows/s, connected nodes
hubble list nodes
```
No `hubble` CLI yet? It is a separate binary from the `cilium` CLI:
```bash
HUBBLE_VERSION=$(curl -fsSL https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -fsSL "https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz" | tar -xz -C ~/.local/bin
```

## 1. Baseline flows (no policy)
```bash
./up.sh policy none
hubble observe -n cilium-lab --last 30
./up.sh test ; hubble observe -n cilium-lab --since 1m -o compact
```
- Find a flow from `cilium-lab/xwing` to `cilium-lab/deathstar-...`. What verdict does it have? (FORWARDED)
- Which flows go to `kube-system/coredns`? Why do you see several per curl? (search-path lookups, A + AAAA)
- Note the identity numbers shown with `-o json | jq '.flow.source.identity'` and match them with `kubectl get ciliumidentities`.

## 2. Watch an L3/L4 drop
```bash
./up.sh policy l3l4
hubble observe -n cilium-lab --verdict DROPPED -f &        # leave it running
kubectl -n cilium-lab exec xwing -- curl -s -m 3 -XPOST deathstar/v1/request-landing ; kill %%
```
- What is the drop reason? (`Policy denied`)
- Why does the client see a timeout and not a reset? (the SYN is dropped silently)
- `hubble observe -n cilium-lab --from-label org=alliance --to-label class=deathstar` - filter by labels instead of pod names.

## 3. L7 visibility and an L7 deny
```bash
./up.sh policy l7
hubble observe -n cilium-lab --protocol http --last 20
kubectl -n cilium-lab exec tiefighter -- curl -s -XPUT deathstar/v1/exhaust-port
hubble observe -n cilium-lab --protocol http --http-method PUT --last 5
```
- Which verdict does the PUT get in Hubble? (DROPPED, with an http 403 response shown)
- Why did `--protocol http` show nothing in exercise 1? (no Envoy redirect without an L7 rule)
- `hubble observe --http-status 403 -n cilium-lab`, `--http-path '/v1/.*'` - practise the L7 filters.

## 4. DNS and FQDN
```bash
./up.sh policy fqdn
hubble observe -n cilium-lab --pod mediabot --protocol dns --last 20
hubble observe -n cilium-lab --pod mediabot --to-fqdn api.github.com --last 10
hubble observe -n cilium-lab --pod mediabot --verdict DROPPED --last 10
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg fqdn cache list | grep github
```
- Which component answered the DNS query first? (the agent's DNS proxy, then kube-dns)
- What is in the FQDN cache and when does an entry expire? (IPs learned per endpoint, DNS TTL + `tofqdns-min-ttl`)
- Change `api.github.com` to `github.com` in the policy, re-apply, and predict the curl results before running them.

## 5. Output formats and filters worth knowing
```bash
hubble observe -n cilium-lab -o json | jq -r '.flow | [.verdict, .source.pod_name, .destination.pod_name] | @tsv' | head
hubble observe --type drop --type policy-verdict --last 20      # event types: trace, drop, l7, policy-verdict, capture ...
hubble observe --not --namespace kube-system --last 20          # negate any filter with --not
hubble observe --port 80 --protocol tcp --to-namespace cilium-lab
hubble observe --identity world --last 20                       # traffic from/to outside the cluster
```

## 6. Hubble UI and metrics
```bash
cilium hubble ui                  # port-forwards and opens http://localhost:12000 ; pick namespace cilium-lab
cilium config view | grep hubble  # which metrics are enabled (hubble-metrics)
```
- In the UI service map: which arrows turn red after `./up.sh policy l3l4`?
- Stretch: `./lab.sh addon monitoring`, then enable `hubble.metrics.enabled="{dns,drop,tcp,flow,http}"` via Helm and find `hubble_drop_total` in Prometheus.

## Questions to answer in your notes
1. Where does the Hubble server run, and what does Hubble relay add?
2. Which flag gives you flows from the last 2 minutes only? (`--since 2m`)
3. Name four verdicts. (FORWARDED, DROPPED, AUDIT, REDIRECTED, TRANSLATED, ERROR)
4. Why can Hubble show pod names for traffic whose IPs it never saw in a Kubernetes object before? (ipcache/identity metadata from the agent)
