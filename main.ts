import { loadConfig } from './config'
import { Solver } from './solver'
import { createApp } from './server'

const config = loadConfig(process.argv)
const solver = new Solver(config)
const { start, stop } = createApp(config, solver)

await start()

const close = async (sig: string) => {
  await stop()
  process.exit(0)
}

process.on('SIGINT', () => void close('SIGINT'))
process.on('SIGTERM', () => void close('SIGTERM'))
