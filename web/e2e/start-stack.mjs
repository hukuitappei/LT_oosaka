import { spawn } from "node:child_process"

const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm"
const children = []
let shuttingDown = false

function startProcess(command, extraEnv = {}) {
  const child = spawn(command, {
    cwd: process.cwd(),
    env: { ...process.env, ...extraEnv },
    stdio: "inherit",
    shell: true,
  })

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return
    }
    shuttingDown = true
    for (const current of children) {
      if (current.pid && current.pid !== child.pid) {
        current.kill("SIGTERM")
      }
    }
    process.exit(code ?? (signal ? 1 : 0))
  })

  children.push(child)
  return child
}

startProcess(`${npmCommand} run mock-api:e2e`)
startProcess(`${npmCommand} run start:e2e`, {
  API_URL: process.env.API_URL || "http://127.0.0.1:4100",
})

function shutdown() {
  if (shuttingDown) {
    return
  }
  shuttingDown = true
  for (const child of children) {
    if (child.pid) {
      child.kill("SIGTERM")
    }
  }
  process.exit(0)
}

process.on("SIGINT", shutdown)
process.on("SIGTERM", shutdown)

setInterval(() => {}, 1000)
