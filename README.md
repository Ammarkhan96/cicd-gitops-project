# GitHub Actions + Docker + Trivy + Helm + Argo CD GitOps CI/CD

A portfolio-ready, low-cost project demonstrating automated testing, container build, vulnerability scanning, immutable image tags, a separate GitOps repository, approval before deployment configuration changes, and Argo CD auto-sync to Kubernetes.

## Architecture

1. Push or open a pull request against `main` in the application repository.
2. GitHub Actions installs dependencies, runs Ruff lint and pytest.
3. On pushes to `main`, the workflow builds a Docker image and scans it with Trivy. The scan fails on detected **CRITICAL** vulnerabilities (including only fixed/unfixed behavior as configured).
4. If the scan passes, the image is pushed to Docker Hub using the full Git commit SHA as the tag.
5. The `production` GitHub Environment gates the GitOps update job if required reviewers are configured.
6. The workflow updates the Helm image tag in the separate GitOps repository and commits it.
7. Argo CD detects the Git change and automatically syncs the Helm chart into Kubernetes.

> This project uses a local Kubernetes cluster for learning. GitHub-hosted runners do not deploy directly into your laptop. Argo CD, running in your local cluster, pulls desired state from GitHub and pulls the container image from Docker Hub.

## Repositories

Create two public repositories (or private ones with appropriate access):

- `github-actions-argocd-app` — contents of `app/`
- `github-actions-argocd-gitops` — contents of `gitops/`

Copy the contents of each folder into its matching repository. Do not push the parent directory as a third repository unless you want a monorepo.

## Prerequisites

- Ubuntu/Linux, Git, Docker, kubectl, kind, Helm, and a GitHub account
- Docker Hub account
- GitHub personal access token with access to write to the GitOps repository

Install missing local tools as needed:

```bash
sudo apt update
sudo apt install -y git curl
```

Install Docker, kubectl, kind and Helm using their official installation guides; versions and installation methods change over time. Verify:

```bash
git --version
docker --version
kubectl version --client
kind version
helm version
```

## Part A — Prepare the application repository

```bash
mkdir github-actions-argocd-app
cd github-actions-argocd-app
```

Copy every file from this bundle's `app/` folder here, including the hidden `.github` folder and `.dockerignore`.

Update `.github/workflows/ci-cd.yml` only if you change names or registry settings. The image repository path is generated as `DOCKERHUB_USERNAME/github-actions-argocd-app` using the `DOCKERHUB_USERNAME` secret.

### Add GitHub Actions secrets and variables

In the **application repo** go to **Settings → Secrets and variables → Actions**.

Repository secrets:

- `DOCKERHUB_USERNAME`: your Docker Hub username
- `DOCKERHUB_TOKEN`: a Docker Hub access token (do not use your account password)
- `GITOPS_TOKEN`: a GitHub token with Contents: Read and write access to the GitOps repository

Repository variable:

- `GITOPS_REPOSITORY`: `YOUR_GITHUB_USERNAME/github-actions-argocd-gitops`

In the workflow, change `YOUR_GITHUB_USERNAME` nowhere else; this variable supplies the full repository name. Never paste tokens into YAML, source files, screenshots, or commits.

### Configure manual approval

In the application repo go to **Settings → Environments → New environment** and create `production`. Configure required reviewers if that feature is available for your repository/plan. The `update-gitops` job references this environment. If no reviewer protection is configured, the environment name alone does not enforce an approval gate.

### Test locally before pushing

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check app.py tests
pytest -q

docker build -t github-actions-argocd-app:local .
docker run --rm -d --name gitops-demo-local -p 8000:8000 github-actions-argocd-app:local
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker stop gitops-demo-local
```

Expected tests: `3 passed`. The root endpoint returns JSON; health and ready endpoints return HTTP 200.

### Push application repo

```bash
git init
git branch -M main
git add .
git commit -m "feat: add Flask app and GitOps CI/CD pipeline"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/github-actions-argocd-app.git
git push -u origin main
```

Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username. Watch the **Actions** tab. A push to `main` should run tests, build/scan/push the image, then pause at the production environment if reviewer protection is enabled.

## Part B — Prepare the GitOps repository

Create `github-actions-argocd-gitops`. Copy all contents of this bundle's `gitops/` folder into it.

Edit `helm/app/values.yaml` and replace `DOCKERHUB_USERNAME` with your actual Docker Hub username. Keep the placeholder tag for the first commit; the pipeline will replace it after a successful image push.

Edit `argocd/application.yaml` and replace `GITHUB_USERNAME` in `repoURL` with your GitHub username.

Then push:

```bash
git init
git branch -M main
git add .
git commit -m "feat: add Helm chart and Argo CD application"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/github-actions-argocd-gitops.git
git push -u origin main
```

The GitOps repo should be accessible to your Argo CD installation. For a private repository, configure repository credentials in Argo CD; for easiest learning, a public GitOps repo avoids that extra step. Never make a repository public if it contains secrets.

## Part C — Create local Kubernetes and install Argo CD

```bash
kind create cluster --name gitops-cicd
kubectl cluster-info --context kind-gitops-cicd
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl rollout status deployment/argocd-server -n argocd --timeout=180s
```

For local access to the Argo CD UI, in one terminal run:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open `https://localhost:8080` and accept the local/self-signed certificate warning. Get the initial admin password in another terminal:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

Username is `admin`. Treat the password as a secret and change it after first login. Keep the port-forward terminal running while using the UI.

Install the application:

```bash
kubectl apply -f argocd/application.yaml
```

Run this command from the **GitOps repository root**, after changing the repository URL. Check:

```bash
kubectl get applications -n argocd
kubectl get pods -n gitops-demo
kubectl get svc -n gitops-demo
```

If you prefer to apply from a local copy in the app repository, copy `argocd/application.yaml` from the GitOps repo first. Argo CD should report `Synced` and `Healthy` after the image tag has been replaced with a real pushed image and the deployment becomes ready.

## Part D — Test the deployed app

```bash
kubectl port-forward -n gitops-demo svc/gitops-demo-gitops-demo 8081:80
```

In another terminal:

```bash
curl http://localhost:8081/
curl http://localhost:8081/health
curl http://localhost:8081/ready
kubectl get pods -n gitops-demo -o wide
kubectl describe application github-actions-argocd-app -n argocd
```

The exact Service name is generated from the Helm release and chart names. If your service name differs, find it with `kubectl get svc -n gitops-demo` and use that name in the port-forward command.

## End-to-end test

1. Change the message or version in `app.py`.
2. Commit and push to `main`.
3. Confirm lint and unit tests pass.
4. Confirm Trivy passes and the image is pushed with the full commit SHA.
5. Approve the `production` environment deployment if reviewers are enabled.
6. Confirm the GitOps repository receives a commit changing `image.tag`.
7. Confirm Argo CD becomes `Synced` / `Healthy` and Kubernetes rolls out new pods.
8. Run the curl checks again.

## Troubleshooting

- **Workflow cannot push GitOps commit:** check `GITOPS_TOKEN` permissions and `GITOPS_REPOSITORY`; ensure token can write Contents to the target repository.
- **Docker login fails:** verify `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`; use a Docker Hub access token.
- **Trivy fails:** inspect the findings. This is intentional when a CRITICAL vulnerability is found. Update the base image/dependencies and rebuild; do not disable scanning just to make the pipeline green.
- **ImagePullBackOff:** check `kubectl describe pod -n gitops-demo POD_NAME`; confirm image repository and SHA tag exist in Docker Hub. For private Docker Hub images, configure Kubernetes imagePullSecrets.
- **Argo CD cannot fetch Git:** verify `repoURL`, branch `main`, and repository visibility/credentials.
- **Application remains OutOfSync:** check Argo CD application events and whether the workflow committed the changed tag to the GitOps repo.
- **Pod fails due to security context:** the chart runs as non-root and uses a read-only root filesystem. This Flask/Gunicorn example should work without writing files; if adding code that writes files, mount a writable `emptyDir` only where required.
- **Local cluster is out of resources:** close heavy apps and check `free -h`; kind runs Kubernetes nodes as Docker containers.

## Rollback

For GitOps, the preferred rollback is to revert the commit in the GitOps repository that changed the image tag. Argo CD sees the revert and reconciles Kubernetes back to the previous image. Alternatively, edit `helm/app/values.yaml` to a previous known-good SHA tag and commit it. Avoid manually editing live Kubernetes resources because Argo CD may reconcile them back to Git's desired state.

## Security notes

- Image tags use the Git commit SHA rather than mutable `latest`.
- Trivy gates image publishing on CRITICAL vulnerabilities.
- The app runs as non-root, drops Linux capabilities and uses a read-only root filesystem.
- Secrets are stored in GitHub Actions Secrets, never in Git.
- Configure least-privilege tokens and production environment reviewers.
- This is a learning project, not a hardened production platform. Pin third-party Actions to reviewed full commit SHAs for production use and review upstream action security before adoption.


Built a CI/CD pipeline with GitHub Actions and Argo CD that builds, tests, scans and deploys a Dockerized application to Kubernetes using GitOps and immutable commit-SHA image tags.
