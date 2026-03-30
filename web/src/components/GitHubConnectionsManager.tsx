"use client"

import type { FormEvent, ReactNode } from "react"
import { useEffect, useState } from "react"
import { api, type GitHubConnection } from "@/lib/api"

type TokenFormState = {
  accessToken: string
  githubAccountLogin: string
  label: string
}

type AppLinkFormState = {
  installationId: string
  githubAccountLogin: string
  label: string
}

const initialTokenForm: TokenFormState = {
  accessToken: "",
  githubAccountLogin: "",
  label: "",
}

const initialAppLinkForm: AppLinkFormState = {
  installationId: "",
  githubAccountLogin: "",
  label: "",
}

export default function GitHubConnectionsManager({
  initialConnections,
  initialError = "",
}: {
  initialConnections: GitHubConnection[]
  initialError?: string
}) {
  const [connections, setConnections] = useState(initialConnections)
  const [tokenForm, setTokenForm] = useState<TokenFormState>(initialTokenForm)
  const [appLinkForm, setAppLinkForm] = useState<AppLinkFormState>(initialAppLinkForm)
  const [tokenError, setTokenError] = useState("")
  const [appLinkError, setAppLinkError] = useState("")
  const [actionError, setActionError] = useState(initialError)
  const [isSaving, setIsSaving] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  async function handleCreateTokenConnection(event: FormEvent) {
    event.preventDefault()
    setTokenError("")
    setActionError("")
    setIsSaving(true)

    try {
      const created = await api.createTokenGitHubConnection({
        access_token: tokenForm.accessToken,
        github_account_login: tokenForm.githubAccountLogin || null,
        label: tokenForm.label || null,
      })
      if (!created) {
        throw new Error("Failed to create token connection")
      }
      setConnections((current) => [created, ...current.filter((connection) => connection.id !== created.id)])
      setTokenForm(initialTokenForm)
    } catch (error) {
      setTokenError(error instanceof Error ? error.message : "Failed to create token connection")
    } finally {
      setIsSaving(false)
    }
  }

  async function handleCreateAppConnection(event: FormEvent) {
    event.preventDefault()
    setAppLinkError("")
    setActionError("")
    setIsSaving(true)

    try {
      const installationId = Number(appLinkForm.installationId)
      if (!Number.isFinite(installationId) || installationId <= 0) {
        throw new Error("Enter a valid installation ID")
      }

      const created = await api.linkAppGitHubConnection({
        installation_id: installationId,
        github_account_login: appLinkForm.githubAccountLogin || null,
        label: appLinkForm.label || null,
      })
      if (!created) {
        throw new Error("Failed to link GitHub App installation")
      }

      setConnections((current) => [created, ...current.filter((connection) => connection.id !== created.id)])
      setAppLinkForm(initialAppLinkForm)
    } catch (error) {
      setAppLinkError(error instanceof Error ? error.message : "Failed to link GitHub App installation")
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDeleteConnection(connection: GitHubConnection) {
    setActionError("")
    const connectionName = connection.label ?? connection.github_account_login ?? `#${connection.id}`
    const confirmed = window.confirm(`Delete connection "${connectionName}"?`)
    if (!confirmed) return

    setIsSaving(true)
    try {
      const result = await api.deleteGitHubConnection(connection.id)
      if (!result) {
        throw new Error("Failed to delete connection")
      }
      setConnections((current) => current.filter((item) => item.id !== connection.id))
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Failed to delete connection")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div
      className="grid gap-6 lg:grid-cols-[1fr_1.15fr]"
      data-testid="github-connections-ready"
      data-hydrated={isHydrated ? "true" : "false"}
    >
      <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="mb-5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.3em] text-amber-300">
            Workspace scope
          </p>
          <h2 className="text-2xl font-semibold text-white">Add a connection</h2>
          <p className="mt-2 text-sm leading-6 text-stone-300">
            Create a workspace-visible personal token or link a GitHub App installation.
          </p>
        </div>

        <div className="space-y-4">
          <form onSubmit={handleCreateTokenConnection} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="mb-3">
              <h3 className="font-medium text-white">Personal token</h3>
              <p className="text-sm text-stone-400">
                Store a token-backed connection for the current workspace.
              </p>
            </div>
            <div className="space-y-3">
              <Field label="Access token" required>
                <input
                  data-testid="github-token-access-token"
                  type="password"
                  value={tokenForm.accessToken}
                  onChange={(event) =>
                    setTokenForm((current) => ({ ...current, accessToken: event.target.value }))
                  }
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="ghp_..."
                  required
                />
              </Field>
              <Field label="GitHub account login">
                <input
                  data-testid="github-token-login"
                  value={tokenForm.githubAccountLogin}
                  onChange={(event) =>
                    setTokenForm((current) => ({ ...current, githubAccountLogin: event.target.value }))
                  }
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="octocat"
                />
              </Field>
              <Field label="Label">
                <input
                  data-testid="github-token-label"
                  value={tokenForm.label}
                  onChange={(event) => setTokenForm((current) => ({ ...current, label: event.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="Personal token"
                />
              </Field>
            </div>
            {tokenError && <p className="mt-3 text-sm text-red-300">{tokenError}</p>}
            <button
              data-testid="github-token-submit"
              type="submit"
              disabled={isSaving}
              className="mt-4 rounded-full bg-amber-300 px-4 py-2 text-sm font-medium text-stone-950 transition-colors hover:bg-amber-200 disabled:opacity-50"
            >
              Save token
            </button>
          </form>

          <form onSubmit={handleCreateAppConnection} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="mb-3">
              <h3 className="font-medium text-white">GitHub App</h3>
              <p className="text-sm text-stone-400">Link an installation by installation ID.</p>
            </div>
            <div className="space-y-3">
              <Field label="Installation ID" required>
                <input
                  data-testid="github-app-installation-id"
                  type="number"
                  min="1"
                  value={appLinkForm.installationId}
                  onChange={(event) =>
                    setAppLinkForm((current) => ({ ...current, installationId: event.target.value }))
                  }
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="123456"
                  required
                />
              </Field>
              <Field label="GitHub account login">
                <input
                  data-testid="github-app-login"
                  value={appLinkForm.githubAccountLogin}
                  onChange={(event) =>
                    setAppLinkForm((current) => ({ ...current, githubAccountLogin: event.target.value }))
                  }
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="octocat"
                />
              </Field>
              <Field label="Label">
                <input
                  data-testid="github-app-label"
                  value={appLinkForm.label}
                  onChange={(event) => setAppLinkForm((current) => ({ ...current, label: event.target.value }))}
                  className="w-full rounded-xl border border-white/10 bg-stone-950 px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-300"
                  placeholder="GitHub App"
                />
              </Field>
            </div>
            {appLinkError && <p className="mt-3 text-sm text-red-300">{appLinkError}</p>}
            <button
              data-testid="github-app-submit"
              type="submit"
              disabled={isSaving}
              className="mt-4 rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10 disabled:opacity-50"
            >
              Link app
            </button>
          </form>
        </div>
      </section>

      <section className="rounded-[1.5rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="mb-5 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-white">Visible connections</h2>
            <p className="text-sm text-stone-400">Connections currently visible in this workspace.</p>
          </div>
          <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-stone-300">
            {connections.length} total
          </span>
        </div>

        {actionError && <p className="mb-4 text-sm text-red-300">{actionError}</p>}

        {!connections.length ? (
          <p className="text-sm text-stone-400">No GitHub connections are visible yet.</p>
        ) : (
          <div className="space-y-3">
            {connections.map((connection) => (
              <article key={connection.id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-medium text-white">{formatConnectionTitle(connection)}</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] uppercase tracking-[0.18em] text-stone-300">
                        {connection.provider_type}
                      </span>
                      {!connection.is_active && (
                        <span className="rounded-full bg-red-300/10 px-2 py-0.5 text-[11px] text-red-200">
                          inactive
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-stone-400">
                      {connection.github_account_login ?? "unknown"}
                    </p>
                    <p className="mt-1 text-xs text-stone-500">
                      installation {connection.installation_id ?? "n/a"} - id #{connection.id}
                    </p>
                  </div>
                  <button
                    data-testid={`github-connection-delete-${connection.id}`}
                    type="button"
                    disabled={isSaving}
                    onClick={() => void handleDeleteConnection(connection)}
                    className="rounded-full border border-red-300/20 px-3 py-1.5 text-sm text-red-200 transition-colors hover:bg-red-300/10 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function Field({
  label,
  required = false,
  children,
}: {
  label: string
  required?: boolean
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm text-stone-300">
        {label}
        {required ? " *" : ""}
      </span>
      {children}
    </label>
  )
}

function formatConnectionTitle(connection: GitHubConnection): string {
  if (connection.label) return connection.label
  if (connection.github_account_login) return connection.github_account_login
  return `Connection #${connection.id}`
}
