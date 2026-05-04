import { spawn } from "node:child_process"
import { once } from "node:events"
import { rmSync } from "node:fs"
import path from "node:path"

const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm"
const isWindows = process.platform === "win32"
const nextDistDir = isWindows ? ".next-e2e" : ".next"
const baseEnv = {
  ...process.env,
  API_URL: "http://localhost:4100",
  NEXT_PUBLIC_API_URL: "http://localhost:4100",
  NEXT_DIST_DIR: nextDistDir,
}
const children = []
let shuttingDown = false

function spawnNpm(args, env = baseEnv) {
  const child =
    process.platform === "win32"
      ? spawn("cmd.exe", ["/c", npmCommand, ...args], {
          cwd: process.cwd(),
          env,
          stdio: "inherit",
        })
      : spawn(npmCommand, args, {
          cwd: process.cwd(),
          env,
          stdio: "inherit",
        })
  children.push(child)
  return child
}

function spawnCommand(command, args, options = {}) {
  return spawn(command, args, {
    cwd: process.cwd(),
    env: options.env ?? baseEnv,
    stdio: options.stdio ?? "pipe",
    shell: options.shell ?? false,
  })
}

async function freePorts(ports) {
  if (process.platform === "win32") {
    const netstat = spawnCommand("netstat", ["-ano"])
    let stdout = ""
    for await (const chunk of netstat.stdout) {
      stdout += chunk.toString()
    }
    await once(netstat, "exit")

    const pids = new Set()
    for (const line of stdout.split(/\r?\n/)) {
      for (const port of ports) {
        if (line.includes(`:${port}`) && line.includes("LISTENING")) {
          const pid = line.trim().split(/\s+/).at(-1)
          if (pid) pids.add(pid)
        }
      }
    }

    for (const pid of pids) {
      const killer = spawnCommand("taskkill", ["/PID", String(pid), "/T", "/F"])
      await once(killer, "exit")
    }
    return
  }

  const lsof = spawnCommand("lsof", ["-ti", ...ports.map((port) => `tcp:${port}`)])
  let stdout = ""
  for await (const chunk of lsof.stdout) {
    stdout += chunk.toString()
  }
  await once(lsof, "exit").catch(() => {})

  const pids = stdout
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter(Boolean)

  for (const pid of pids) {
    try {
      process.kill(Number(pid), "SIGTERM")
    } catch {}
  }
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
  await freePorts([3100, 4100])
  rmSync(path.join(process.cwd(), nextDistDir), { recursive: true, force: true })

  if (!isWindows) {
    const build = spawnNpm(["run", "build"])
    const buildExitCode = await once(build, "exit").then(([code]) => code ?? 1)
    if (buildExitCode !== 0) {
      await shutdown(buildExitCode)
      return
    }
  }

  const mockApi = spawnNpm(["run", "mock-api:e2e"])
  const app = spawnNpm(["run", isWindows ? "dev:e2e" : "start:e2e"])

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
      waitFor("http://localhost:4100/health"),
      waitFor("http://localhost:3100/login"),
    ]),
    earlyExit,
  ])

  const playwright = spawnNpm(["exec", "playwright", "test"], baseEnv)
  const [playwrightExitCode] = await once(playwright, "exit")
  await shutdown(playwrightExitCode ?? 1)
}

main().catch((error) => {
  console.error(error)
  void shutdown(1)
})
