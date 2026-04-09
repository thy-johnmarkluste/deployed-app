"""Dependency installation helpers — npm packages and WordPress plugins."""


class DependencyInstallMixin:
    """Helpers for installing npm dependencies and WordPress plugins."""


    _NPM_DEP_MAP = {
        "tailwindcss":  "tailwindcss @tailwindcss/vite",
        "typescript":   "typescript",
        "sass":         "sass",
        "eslint":       "eslint",
        "prettier":     "prettier",
        "axios":        "axios",
        "react":        "react react-dom @vitejs/plugin-react",
        "vue":          "vue @vitejs/plugin-vue",
    }


    _WP_PLUGIN_MAP = {
        "woocommerce":    "woocommerce",
        "elementor":      "elementor",
        "yoast-seo":      "wordpress-seo",
        "rank-math":      "seo-by-rank-math",
        "wordfence":      "wordfence",
        "contact-form-7": "contact-form-7",
        "advanced-custom-fields": "advanced-custom-fields",
        "all-in-one-wp-migration": "all-in-one-wp-migration",
        "updraftplus":    "updraftplus",
        "wp-super-cache": "wp-super-cache",
        "query-monitor":  "query-monitor",
    }

    _WP_THEME_MAP = {
        "theme-astra": "astra",
        "theme-generatepress": "generatepress",
        "theme-kadence": "kadence",
        "theme-neve": "neve",
        "theme-blocksy": "blocksy",
        "theme-hello-elementor": "hello-elementor",
    }

    def _install_npm_dependencies(self, client, subdomain, dependencies, v):
        """Install selected npm packages in the subdomain folder."""
        path = self.git_manager.get_subdomain_path(subdomain)
        packages = []
        for dep in dependencies:
            pkgs = self._NPM_DEP_MAP.get(dep)
            if pkgs:
                packages.append(pkgs)

        if not packages:
            return

        pkg_str = " ".join(packages)
        v.log(f"\n--- Installing npm dependencies ---")
        v.log(f"Packages: {pkg_str}")
        self.view.status_var.set("Installing npm dependencies...")

        cmd = f"cd '{path}' && npm install --save-dev {pkg_str} 2>&1"
        _, stdout, _ = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        if output:
            for line in output.split('\n')[-10:]:
                if line.strip():
                    v.log(f"  {line.strip()}")

        v.log("npm dependency installation complete.")

    def _install_wp_dependencies(self, client, subdomain, dependencies, v):
        """Install selected WordPress plugins via WP-CLI."""
        path = self.git_manager.get_subdomain_path(subdomain)


        install_cli = "wp-cli" in dependencies
        if install_cli:
            v.log("\n--- Installing WP-CLI ---")
            self.view.status_var.set("Installing WP-CLI...")
            cli_cmds = (
                "curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && "
                "chmod +x wp-cli.phar && "
                "mv -f wp-cli.phar /usr/local/bin/wp 2>&1"
            )
            _, stdout, _ = client.exec_command(cli_cmds)
            out = stdout.read().decode().strip()
            if out:
                v.log(f"  {out}")
            v.log("WP-CLI installed.")

        plugins = []
        for dep in dependencies:
            slug = self._WP_PLUGIN_MAP.get(dep)
            if slug:
                plugins.append(slug)

        if not plugins:
            return

        v.log(f"\n--- Installing WordPress plugins ---")
        self.view.status_var.set("Installing WordPress plugins...")

        for plugin in plugins:
            v.log(f"Installing plugin: {plugin}...")
            cmd = f"cd '{path}' && wp plugin install {plugin} --activate --allow-root 2>&1"
            _, stdout, _ = client.exec_command(cmd)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n')[-5:]:
                    if line.strip():
                        v.log(f"  {line.strip()}")

        v.log("WordPress plugin installation complete.")

        themes = []
        for dep in dependencies:
            slug = self._WP_THEME_MAP.get(dep)
            if slug:
                themes.append(slug)

        if not themes:
            return

        v.log(f"\n--- Installing WordPress themes ---")
        self.view.status_var.set("Installing WordPress themes...")

        for idx, theme in enumerate(themes):
            v.log(f"Installing theme: {theme}...")
            activate_flag = " --activate" if idx == 0 else ""
            cmd = f"cd '{path}' && wp theme install {theme}{activate_flag} --allow-root 2>&1"
            _, stdout, _ = client.exec_command(cmd)
            output = stdout.read().decode().strip()
            if output:
                for line in output.split('\n')[-5:]:
                    if line.strip():
                        v.log(f"  {line.strip()}")

        v.log("WordPress theme installation complete.")
