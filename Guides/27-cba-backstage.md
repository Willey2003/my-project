---
tags: [devops-prep, guide]
---
# Phase 27 - CBA: Certified Backstage Associate

**Golden track step:** G7 · 17-26 Jun 2027 (see schedule) · **Hours:** 40 · **Exam:** CBA, 90 min online multiple choice, USD 250 (verify price and format on training.linuxfoundation.org) · **Lab:** `lab/golden/platform/backstage/`

Backstage is the most common frame for an Internal Developer Platform (IDP) portal, so this phase feeds straight into
phase 28 (CNPA/CNPE). The exam is heavy on "how do I customise and run it": config files, the catalog YAML, the
scaffolder, TechDocs, and the plugin/backend system. You need a working local Backstage app - reading is not enough.

| Week | Focus | Deliverable |
|---|---|---|
| Study week 1 | Architecture, create-app, monorepo layout, app-config layering, Postgres, Docker image | Local Backstage via `backstage/up.sh`, running on Postgres |
| Study week 2 | Software catalog: entity kinds, relations, catalog-info.yaml, locations, providers, annotations | Lab catalog (system, 2 components, API, group) registered and graph visible |
| Study week 3 | Scaffolder templates + custom action; TechDocs (local builder, then techdocs-cli) | `new-service` template creating a repo that shows up in the catalog with docs |
| Study week 4 | Auth + permissions, plugin development (frontend + backend), upgrades, mock exams, sit CBA | CBA |

## Domains (verify the current curriculum on github.com/cncf/curriculum before you book)
| Domain | Weight | Your lab |
|---|---|---|
| Customizing Backstage | 32% | Plugins, themes, app/backend wiring, permission policy, custom scaffolder action |
| Backstage Development Workflow | 24% | `yarn` scripts, backstage-cli, monorepo packages, `versions:bump`, testing |
| Backstage Infrastructure | 22% | app-config layering, Postgres, Docker image, compose/Kubernetes deploy, auth providers |
| Backstage Catalog | 22% | `backstage/catalog/*.yaml`, entity kinds, relations, ingestion |

## Architecture
```
Browser --> app (React SPA, packages/app)  --HTTP /api/<pluginId>-->  backend (Node.js, packages/backend)
                 frontend plugins                                       backend plugins + modules
                                                                        |-- database (SQLite dev / PostgreSQL prod, one logical DB per plugin)
                                                                        |-- integrations (GitHub, GitLab, Azure DevOps...), cache, scheduler
```
- **App (frontend):** single-page React app. Frontend plugins add pages, entity tabs/cards, sidebar items. `packages/app/src/App.tsx`
  wires routes (legacy system); the **new frontend system** uses extensions discovered from installed packages (`@backstage/frontend-defaults`).
- **Backend:** one Node process built with the **new backend system**: `const backend = createBackend(); backend.add(import('@backstage/plugin-catalog-backend')); backend.start();`
  in `packages/backend/src/index.ts`. Each plugin gets its own router under `/api/<pluginId>` and its own database/schema.
- **Plugins:** everything is a plugin - catalog, scaffolder, techdocs, search, kubernetes, permission, auth. Package roles:
  `frontend-plugin`, `backend-plugin`, `backend-plugin-module` (extends another plugin via extension points), `common-library`, `web-library`, `node-library`.
- **Core services** injected into backend plugins: `logger`, `config` (rootConfig), `database`, `httpRouter`, `scheduler`, `urlReader`,
  `discovery`, `auth`, `httpAuth`, `userInfo`, `permissions`, `cache`, `lifecycle`.
- **Monorepo:** created by `npx @backstage/create-app@latest`, Yarn workspaces (`packages/*` for app+backend, `plugins/*` for your plugins).
  Dev ports: frontend 3000, backend 7007.

**Configuration:** `app-config.yaml` (base) + `app-config.local.yaml` (dev secrets, git-ignored) + `app-config.production.yaml` (prod).
Later `--config` files override earlier ones. Environment substitution: `${GITHUB_TOKEN}`; `$file: ./secret.txt`, `$env: VAR`,
`$include: other.yaml`. Override any key from the environment with `APP_CONFIG_<path_with_underscores>` (e.g. `APP_CONFIG_backend_baseUrl`).
Frontend-visible keys must be marked `@visibility frontend` in a config schema; everything else stays in the backend.

**Development workflow commands:**
```bash
npx @backstage/create-app@latest          # scaffold a new app (asks for a name)
yarn install && yarn start                # app on :3000 + backend on :7007 (older apps: yarn dev)
yarn tsc                                  # type-check the whole monorepo
yarn test / yarn lint                     # jest + eslint through backstage-cli
yarn build:backend                        # bundle backend (packages/backend/dist) for the image
yarn build-image                          # docker build using packages/backend/Dockerfile (host build)
yarn new                                  # create a plugin/module/library from the CLI templates
yarn backstage-cli versions:bump          # upgrade all @backstage/* deps to the latest release (then check the upgrade helper)
yarn backstage-cli info                   # versions for bug reports
```

## Software catalog
The catalog is the centre of Backstage: a registry of every software entity, who owns it, and how things relate.
Entities are YAML descriptor files (normally `catalog-info.yaml` in the repo root), ingested and refreshed by the catalog backend.

**Envelope (every kind):**
```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payments-api            # [a-z0-9A-Z-_.], max 63 chars, unique per kind+namespace
  namespace: default            # optional, default "default"
  title: Payments API
  description: Charges cards and issues refunds
  labels: { tier: backend }
  annotations:
    github.com/project-slug: acme/payments-api
    backstage.io/techdocs-ref: dir:.
  tags: [python, payments]
  links: [{ url: https://grafana.example.com/d/payments, title: Dashboard }]
spec: { ... kind-specific ... }
```
Entity reference format: `[kind:][namespace/]name`, e.g. `component:default/payments-api`, `group:team-payments`, `user:default/jdoe`.

**Entity kinds you must know:**
| Kind | What it is | Key spec fields |
|---|---|---|
| Component | A piece of software (service, website, library) | `type`, `lifecycle` (experimental/production/deprecated), `owner`, `system`, `providesApis`, `consumesApis`, `dependsOn` |
| API | An interface a component provides | `type` (openapi, asyncapi, graphql, grpc), `lifecycle`, `owner`, `system`, `definition` (inline or `$text: ./openapi.yaml`) |
| Resource | Infrastructure a component needs (database, bucket, queue) | `type`, `owner`, `system`, `dependsOn` |
| System | A collection of components, APIs and resources that deliver one capability | `owner`, `domain` |
| Domain | A business area grouping systems | `owner`, `subdomainOf` |
| Group | A team or org unit | `type` (team, business-unit...), `profile`, `parent`, `children` (required, may be []), `members` |
| User | A person | `profile`, `memberOf` |
| Location | Pointer to more descriptor files | `type: url`, `target` / `targets` |
| Template | A scaffolder template (apiVersion `scaffolder.backstage.io/v1beta3`) | `parameters`, `steps`, `output` |

**Relations** are generated from spec fields (both directions): `ownedBy`/`ownerOf`, `partOf`/`hasPart`,
`providesApi`/`apiProvidedBy`, `consumesApi`/`apiConsumedBy`, `dependsOn`/`dependencyOf`, `parentOf`/`childOf`, `memberOf`/`hasMember`.
The catalog graph plugin draws them; ownership drives "My groups/owned" filters and permission rules like `isEntityOwner`.

**Ingestion:**
- **Locations** - static in `app-config.yaml` (`catalog.locations: [{type: file, target: ../../catalog/all.yaml}]` or `type: url` to a Git file),
  or registered in the UI (`/catalog-import`, "Register existing component"). A Location can point at more Locations.
- **Entity providers** - push entities from external systems on a schedule: GitHub discovery (all `catalog-info.yaml` in an org),
  GitHub/GitLab org (Users/Groups), Microsoft Graph and LDAP for org data. Configured under `catalog.providers.*` + installed as backend modules.
- **Processors** - run on every entity during the processing loop (validate, emit relations, read `$text` references).
- **Rules:** `catalog.rules: [{allow: [Component, API, System, Domain, Resource, Group, User, Location, Template]}]` - which kinds a location may add.
- **Refresh loop:** entities are re-processed periodically; unregistering removes the location, and entities whose source vanished become **orphans**
  (`backstage.io/orphan: 'true'`), deleted manually or by `catalog.orphanStrategy: delete`.
- Useful annotations: `backstage.io/managed-by-location`, `backstage.io/source-location`, `backstage.io/techdocs-ref`, `backstage.io/kubernetes-id`,
  `github.com/project-slug`, `backstage.io/view-url` / `edit-url`.
- Troubleshoot: entity missing -> check the location is registered, `catalog.rules`, YAML validity, and processing errors on the entity's "Inspect entity" view.

## Software templates (scaffolder)
A Template entity = input form (JSON Schema `parameters`) + ordered `steps` (actions) + `output` (links shown at the end).
```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata: { name: new-service, title: New service }
spec:
  owner: group:team-platform
  type: service
  parameters:
    - title: Service
      required: [name, owner]
      properties:
        name: { type: string, pattern: '^[a-z0-9-]+$' }
        owner: { type: string, ui:field: OwnerPicker, ui:options: { catalogFilter: { kind: Group } } }
    - title: Repository
      properties:
        repoUrl: { type: string, ui:field: RepoUrlPicker, ui:options: { allowedHosts: [github.com] } }
  steps:
    - { id: fetch, name: Fetch skeleton, action: fetch:template, input: { url: ./skeleton, values: { name: '${{ parameters.name }}' } } }
    - { id: publish, name: Publish, action: publish:github, input: { repoUrl: '${{ parameters.repoUrl }}' } }
    - { id: register, name: Register, action: catalog:register, input: { repoContentsUrl: '${{ steps.publish.output.repoContentsUrl }}', catalogInfoPath: /catalog-info.yaml } }
  output:
    links: [{ title: Repository, url: '${{ steps.publish.output.remoteUrl }}' }]
```
- Template syntax is Nunjucks-style `${{ }}`; filters like `parseRepoUrl`, `pick`, `projectSlug`. Inside skeleton files use `${{ values.x }}`.
- Built-in actions: `fetch:plain`, `fetch:template`, `fetch:plain:file`, `publish:github|gitlab|bitbucket...`, `catalog:register`, `catalog:write`,
  `debug:log`, `github:actions:dispatch`. The page `/create/actions` lists what your install has.
- Field extensions (`ui:field`): `EntityPicker`, `OwnerPicker`, `RepoUrlPicker`, `EntityNamePicker`, `EntityTagsPicker`, `MyGroupsPicker`; write your own with `createScaffolderFieldExtension`.
- **Custom action:** `createTemplateAction({ id: 'acme:create-ticket', schema: {...}, async handler(ctx) { ctx.logger.info(...); ctx.output('ticket', id) } })`,
  registered from a backend module through the `scaffolderActionsExtensionPoint`.
- Template editor at `/create/edit` does dry runs (no publishing) - use it while iterating. Tasks run in the backend; logs show per step.

## TechDocs
Docs-like-code: Markdown in the repo, built with MkDocs + the `mkdocs-techdocs-core` plugin, rendered inside the entity page.
- Repo needs `mkdocs.yml` (`site_name`, `nav`, `plugins: [techdocs-core]`), a `docs/` folder, and the annotation `backstage.io/techdocs-ref: dir:.`.
- `techdocs.builder: local` - the backend generates docs on first view (generator `runIn: docker` or `local` with mkdocs installed).
- `techdocs.builder: external` - CI generates and publishes; Backstage only reads. Recommended for production.
- Publishers: `local` (filesystem), `awsS3`, `googleGcs`, `azureBlobStorage`, `openStackSwift`.
```bash
npx @techdocs/cli serve                                     # preview docs for the repo you are in
npx @techdocs/cli generate --no-docker --output-dir site    # build
npx @techdocs/cli publish --publisher-type awsS3 --storage-name my-bucket --entity default/component/payments-api
```

## Auth and permissions basics
- **Authentication** (who are you): auth providers configured under `auth.providers.<name>.<env>` - `github`, `gitlab`, `google`, `microsoft`,
  `okta`, `oidc`, `oauth2Proxy`, and `guest` (dev only). Installed as backend modules (`@backstage/plugin-auth-backend-module-github-provider`).
- **Sign-in resolver** maps the provider identity to a catalog **User** entity: `usernameMatchingUserEntityName`,
  `emailMatchingUserEntityProfileEmail`, `emailLocalPartMatchingUserEntityName`. No matching User = sign-in fails - so ingest org data first.
- The result is a **Backstage identity**: user entity ref + ownership refs (the user and their groups), carried in a Backstage token.
- **Service-to-service:** plugins call each other with plugin tokens issued by the `auth` core service; external callers use
  `backend.auth.externalAccess` (static tokens, JWKS, legacy keys) with optional access restrictions per plugin.
- **Permissions framework** (authorization): `permission.enabled: true` + a policy in the permission backend.
  A `PermissionPolicy` implements `handle(request, user)` and returns `AuthorizeResult.ALLOW`, `DENY`, or `CONDITIONAL`
  (e.g. `catalogConditions.isEntityOwner` so only owners can `catalog.entity.delete`). Plugins declare permissions
  (`catalogEntityDeletePermission`, `scaffolderTemplateParameterReadPermission`...) and check them with the `permissions` service.
  The allow-all policy module exists for development only. Frontend hides buttons with `usePermission` / `RequirePermission`, but the backend is the enforcement point.

## Plugin development basics
```bash
yarn new                          # choose: frontend-plugin | backend-plugin | backend-plugin-module | plugin-common | node-library ...
cd plugins/hello && yarn start    # frontend plugin in isolation (dev/ folder) ; backend plugin: yarn start runs it standalone
```
Frontend plugin (legacy system): `createPlugin({ id: 'hello', routes })`, pages via `createRoutableExtension`, entity cards via
`createComponentExtension`, APIs with `createApiRef` + `createApiFactory`, consumed with `useApi(ref)`. Wire it: route in `App.tsx`,
card in `packages/app/src/components/catalog/EntityPage.tsx`. New frontend system: `createFrontendPlugin` + extension blueprints (`PageBlueprint`, `EntityCardBlueprint`), enabled via `app.extensions` config.

Backend plugin (new backend system):
```ts
export const helloPlugin = createBackendPlugin({
  pluginId: 'hello',
  register(env) {
    env.registerInit({
      deps: { logger: coreServices.logger, httpRouter: coreServices.httpRouter, database: coreServices.database },
      async init({ logger, httpRouter }) {
        const router = Router(); router.get('/health', (_, res) => res.json({ status: 'ok' }));
        httpRouter.use(router);                       // served at /api/hello/health
        httpRouter.addAuthPolicy({ path: '/health', allow: 'unauthenticated' });
      },
    });
  },
});
```
- **Modules** (`createBackendModule({ pluginId: 'catalog', moduleId: 'my-provider', ... })`) extend a plugin through its **extension points**
  (e.g. `catalogProcessingExtensionPoint`, `scaffolderActionsExtensionPoint`) - this is how you add providers, processors, actions.
- Install: `yarn --cwd packages/backend add @internal/plugin-hello-backend` and `backend.add(import('@internal/plugin-hello-backend'))`.
- Testing: `@backstage/test-utils` / `renderInTestApp` (frontend), `@backstage/backend-test-utils` `startTestBackend` + `mockServices` (backend).
- Share plugins via npm; browse existing ones in the Backstage plugin directory before writing your own.
- Customise look: custom theme (`createUnifiedTheme`), sidebar items, logos, homepage plugin - all "Customizing Backstage" exam material.

## Infrastructure and deployment
- Database: `backend.database.client: better-sqlite3` (dev, in-memory) vs `pg` with `connection: {host, port, user, password}` (prod). Plugins get separate databases (or schemas with `pluginDivisionMode: schema`).
- Image: **host build** (`yarn install --immutable && yarn tsc && yarn build:backend && yarn build-image`) or a multi-stage Dockerfile. The backend serves the built frontend (app-backend plugin), so one container on :7007 is enough.
- Kubernetes: Deployment + Service + Postgres (StatefulSet or managed), config via ConfigMap + Secrets as env vars; or the community Helm chart (`backstage/charts`).
- Scale: backend is stateless apart from the DB; several replicas are fine (scheduler coordinates tasks via the DB).
- Other integrations: `integrations.github[].token` for reading repos; `kubernetes` plugin for workload status on entity pages; `search` backend (Lunr dev, Postgres/Elasticsearch prod).

## Lab walkthrough (`lab/golden/platform/backstage/`)
1. Read `README.md`, then `./up.sh` - it runs `create-app` into `./app` (first time), builds the image, and starts Postgres + Backstage with `docker-compose.yaml`.
2. Open http://localhost:7007, sign in as guest. Catalog shows `team-payments`, the `payments` system, `payments-api`, `payments-web` and the `payments-api` API.
3. Open the catalog graph for `payments` - find each relation from the table above and the YAML field that created it.
4. Break it: change `owner: group:team-payments` to a group that does not exist, wait for refresh (or restart), read the processing error in "Inspect entity".
5. Scaffolder: `/create` -> "New service". Dry run it in `/create/edit`. For a real run, export `GITHUB_TOKEN` before `./up.sh`.
6. TechDocs: open the Docs tab of a component created from the template (the skeleton ships `mkdocs.yml` + `docs/`).
7. In `./app`: `yarn new` a backend plugin with a `/health` route, add it to the backend, rebuild, `curl localhost:7007/api/<id>/health`.
8. Swap the guest provider for GitHub OAuth in `app-config.local.yaml` and add a User entity whose name matches your GitHub login.

## Self-check
1. Which two packages make up a new Backstage app, and what runs where?
2. How does the new backend system register a plugin?
3. In what order are `app-config.yaml`, `app-config.local.yaml` and `app-config.production.yaml` applied, and how do you override a key from the environment?
4. Write the entity reference for the group `team-payments` in the default namespace.
5. Which entity kind groups components, APIs and resources that deliver one capability? Which groups those?
6. What spec field on a Component creates the `providesApi` relation?
7. What does `children: []` on a Group tell you about required fields?
8. Name three ways entities get into the catalog.
9. What is an orphaned entity and how does it happen?
10. What does `catalog.rules` control?
11. Which apiVersion does a Template use, and what are its three main spec sections?
12. What does `fetch:template` do differently from `fetch:plain`?
13. How do you add a custom scaffolder action?
14. Which annotation turns on TechDocs for an entity, and what files must the repo contain?
15. When would you choose the `external` TechDocs builder?
16. What does a sign-in resolver do and what happens if it finds no match?
17. Name the three results a permission policy can return.
18. What is the difference between a backend plugin and a backend module?
19. Which command upgrades all Backstage packages in an app?
20. Which database do you use in production and why not SQLite?

<details><summary>Answers</summary>

1. `packages/app` (React frontend, runs in the browser) and `packages/backend` (Node.js, runs plugins' APIs, talks to the DB and integrations).
2. `backend.add(import('<plugin-package>'))` in `packages/backend/src/index.ts`, then `backend.start()`.
3. In the order given with `--config`; later files win (`yarn start` loads base + local). Environment: `APP_CONFIG_<path_with_underscores>` or `${VAR}` substitution.
4. `group:default/team-payments` (short form `group:team-payments`).
5. System; Domain groups systems.
6. `spec.providesApis: [<api ref>]`.
7. `spec.type` and `spec.children` are required on Group (children may be empty); `members` and `parent` are optional.
8. Static `catalog.locations` in config, registering a URL in the UI (or via API), entity providers (GitHub discovery, org providers, LDAP, MS Graph).
9. An entity whose parent location no longer emits it (file deleted, location changed); it gets `backstage.io/orphan: 'true'` and stays until deleted or `orphanStrategy: delete`.
10. Which entity kinds may be ingested (globally or per location).
11. `scaffolder.backstage.io/v1beta3`; `parameters`, `steps`, `output`.
12. `fetch:template` renders the files with the template engine (`${{ values.x }}`); `fetch:plain` copies them untouched.
13. `createTemplateAction` in a backend module registered with `scaffolderActionsExtensionPoint`, then `backend.add` the module.
14. `backstage.io/techdocs-ref: dir:.`; `mkdocs.yml` (with techdocs-core) and a `docs/` folder.
15. Production: CI builds docs and publishes to object storage, keeping mkdocs/docker out of the Backstage backend and scaling better.
16. Maps the external identity to a catalog User entity to issue a Backstage identity; with no match, sign-in is rejected.
17. ALLOW, DENY, CONDITIONAL (conditions evaluated by the owning plugin, e.g. isEntityOwner).
18. A plugin owns an API/router and its data (`createBackendPlugin`); a module extends an existing plugin via its extension points (`createBackendModule`).
19. `yarn backstage-cli versions:bump` (then follow the upgrade helper for template changes).
20. PostgreSQL - persistent, multi-replica safe, supported for search and scheduling; SQLite in-memory loses data on restart and is single-process.
</details>

## Resources
https://backstage.io/docs (architecture overview, software catalog, software templates, TechDocs, auth, permissions, backend system) ·
https://backstage.io/docs/features/software-catalog/descriptor-format · https://backstage.io/plugins · https://github.com/cncf/curriculum (CBA PDF) ·
Linux Foundation LFS142 "Introduction to Backstage" (free) · Backstage upgrade helper: https://backstage.github.io/upgrade-helper


---
[[Home]] · [[Schedule]]
