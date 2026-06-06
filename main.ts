import { loadConfig } from './config'
import { Solver } from './solver'
import { createApp } from './server'

const config = loadConfig(process.argv)

const solver = new Solver(config)
const { start, stop } = createApp(config, solver)

await start()

const shutdown = async (signal: string) => {
  console.log(`\n[server] ${signal}`)
  await stop()
  process.exit(0)
}

process.on('SIGINT', () => void shutdown('SIGINT'))
process.on('SIGTERM', () => void shutdown('SIGTERM'))
