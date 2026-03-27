import { spawn } from "node:child_process"
import { once } from "node:events"

const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm"
const baseEnv = { ...process.env, API_URL: "http://127.0.0.1:4100" }
const children = []
let shuttingDown = false

function spawnShell(command, env = baseEnv) {
  const child = spawn(command, {
    cwd: process.cwd(),
    env,
    stdio: "inherit",
    shell: true,
  })
  children.push(child)
  return child
}

async function waitFor(url, timeoutMs = 120000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url)
      if (response.ok) {
        return
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

async function stopChild(child) {
  if (!child.pid || child.exitCode !== null) {
    return
  }

  if (process.platform === "win32") {
    const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      shell: true,
    })
    await once(killer, "exit")
    return
  }

  child.kill("SIGTERM")
  await once(child, "exit")
}

async function shutdown(exitCode = 0) {
  if (shuttingDown) {
    return
  }
  shuttingDown = true
  await Promise.all(children.map((child) => stopChild(child)))
  process.exit(exitCode)
}

process.on("SIGINT", () => {
  void shutdown(1)
})
process.on("SIGTERM", () => {
  void shutdown(1)
})

async function main() {
  const build = spawnShell(`${npmCommand} run build`)
  const buildExitCode = await once(build, "exit").then(([code]) => code ?? 1)
  if (buildExitCode !== 0) {
    await shutdown(buildExitCode)
    return
  }

  const mockApi = spawnShell(`${npmCommand} run mock-api:e2e`)
  const app = spawnShell(`${npmCommand} run start:e2e`)

  const earlyExit = new Promise((_, reject) => {
    for (const child of [mockApi, app]) {
      child.once("exit", (code) => {
        if (!shuttingDown && code !== 0) {
          reject(new Error(`E2E stack process exited early with code ${code}`))
        }
      })
    }
  })

  await Promise.race([
    Promise.all([
      waitFor("http://127.0.0.1:4100/health"),
      waitFor("http://127.0.0.1:3100/login"),
    ]),
    earlyExit,
  ])

  const playwright = spawnShell(`${npmCommand} exec playwright test`, baseEnv)
  playwright.on("exit", (code) => {
    void shutdown(code ?? 1)
  })
}

main().catch((error) => {
  console.error(error)
  void shutdown(1)
})
