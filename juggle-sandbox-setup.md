name 	description
sandbox-setup
	
Configure Claude Code sandbox settings for this repository
Sandbox Setup Skill

Configure Claude Code for optimal autonomous agent execution in this repository.
What This Skill Does

    Analyzes your codebase to detect:
        Programming languages (Go, Python, Node.js, Rust, etc.)
        Package managers (go mod, npm, pip, cargo, etc.)
        Build tools and test runners
        Dev servers and their ports

    Generates tailored permissions for .claude/settings.json:
        Allow commands for detected tools
        Network access for package registries
        File system permissions for build outputs

    Preserves existing settings:
        Merges with hooks configuration
        Keeps deny rules for secrets
        Maintains ask rules for git push

How to Use

When invoked, I will:

    Scan the repository for configuration files (package.json, go.mod, Cargo.toml, requirements.txt, etc.)
    Ask clarifying questions about your workflow
    Present proposed settings for your approval
    Update .claude/settings.json

Detection Patterns

I look for these files to detect your stack:

    go.mod → Go (go build, go test, go mod)
    package.json → Node.js (npm, yarn, pnpm, node)
    Cargo.toml → Rust (cargo build, cargo test)
    requirements.txt / pyproject.toml → Python (pip, python, pytest)
    Gemfile → Ruby (bundle, ruby, rake)
    pom.xml / build.gradle → Java (mvn, gradle)
    devbox.json → Devbox (devbox run)

Settings Structure

The generated settings follow this structure:

{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true
  },
  "permissions": {
    "allow": ["Bash(detected-tools:*)"],
    "deny": ["Read(./.env)", "Read(./secrets/**)"],
    "ask": ["Bash(juggle agent:*)", "Bash(git push:*)"]
  },
  "hooks": { ... }
}
