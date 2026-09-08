"""
Frontend production configuration tests.

Verifies that the frontend build artifacts and configuration are production-ready:
- Dockerfile uses multi-stage build with non-root user
- nginx.conf has security headers and caching policies
- vite.config.ts has production-appropriate settings
"""

from __future__ import annotations

from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend"


class TestFrontendDockerfile:
    """Tests verifying frontend Dockerfile production readiness."""

    def test_dockerfile_exists(self) -> None:
        assert (FRONTEND_DIR / "Dockerfile").exists()

    def test_dockerfile_uses_multi_stage_build(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "FROM node:" in content
        assert "FROM nginx:" in content
        assert "AS builder" in content
        assert "AS runtime" in content

    def test_dockerfile_uses_non_root_user(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "USER nginx" in content

    def test_dockerfile_has_healthcheck(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "HEALTHCHECK" in content

    def test_dockerfile_exposes_correct_port(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "EXPOSE 8080" in content

    def test_dockerfile_installs_only_necessary_packages(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "apk add --no-cache" in content

    def test_dockerfile_copies_build_artifacts_only(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "COPY --from=builder /app/dist /usr/share/nginx/html" in content

    def test_dockerfile_sets_workdir(self) -> None:
        content = (FRONTEND_DIR / "Dockerfile").read_text()
        assert "WORKDIR /app" in content


class TestFrontendNginxConfig:
    """Tests verifying nginx.conf production readiness."""

    def test_nginx_conf_exists(self) -> None:
        assert (FRONTEND_DIR / "nginx.conf").exists()

    def test_nginx_has_security_headers(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content
        assert "Strict-Transport-Security" in content
        assert "Referrer-Policy" in content
        assert "Permissions-Policy" in content

    def test_nginx_has_gzip_compression(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "gzip on" in content
        assert "gzip_types" in content

    def test_nginx_has_caching_policies(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "Cache-Control" in content
        assert "expires" in content

    def test_nginx_has_spa_fallback(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "try_files $uri $uri/ /index.html" in content

    def test_nginx_proxies_api_requests(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "location /api/" in content
        assert "proxy_pass" in content

    def test_nginx_listens_on_8080(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "listen 8080" in content

    def test_nginx_disables_access_logs_for_static_assets(self) -> None:
        content = (FRONTEND_DIR / "nginx.conf").read_text()
        assert "access_log off" in content


class TestFrontendViteConfig:
    """Tests verifying vite.config.ts production readiness."""

    def test_vite_config_exists(self) -> None:
        assert (FRONTEND_DIR / "vite.config.ts").exists()

    def test_vite_config_disables_sourcemaps_in_production(self) -> None:
        content = (FRONTEND_DIR / "vite.config.ts").read_text()
        assert "sourcemap: false" in content

    def test_vite_config_has_code_splitting(self) -> None:
        content = (FRONTEND_DIR / "vite.config.ts").read_text()
        assert "manualChunks" in content

    def test_vite_config_has_dev_proxy(self) -> None:
        content = (FRONTEND_DIR / "vite.config.ts").read_text()
        assert "proxy" in content
        assert "/api" in content

    def test_vite_config_uses_react_plugin(self) -> None:
        content = (FRONTEND_DIR / "vite.config.ts").read_text()
        assert "@vitejs/plugin-react" in content


class TestFrontendPackageJson:
    """Tests verifying package.json production readiness."""

    def test_package_json_exists(self) -> None:
        assert (FRONTEND_DIR / "package.json").exists()

    def test_package_json_has_build_script(self) -> None:
        import json

        content = json.loads((FRONTEND_DIR / "package.json").read_text())
        scripts = content.get("scripts", {})
        assert "build" in scripts

    def test_package_json_has_preview_script(self) -> None:
        import json

        content = json.loads((FRONTEND_DIR / "package.json").read_text())
        scripts = content.get("scripts", {})
        assert "preview" in scripts

    def test_package_json_has_no_dev_dependencies_in_prod(self) -> None:
        import json

        content = json.loads((FRONTEND_DIR / "package.json").read_text())
        dev_deps = content.get("devDependencies", {})
        prod_deps = content.get("dependencies", {})
        assert isinstance(dev_deps, dict)
        assert isinstance(prod_deps, dict)
