/* 临时诊断脚本：定位 electron 二进制解压卡死/静默失败的精确环节。用完即删。 */
const fs = require('fs')
const path = require('path')

const FRONTEND = __dirname
const ELECTRON_PKG = path.join(FRONTEND, 'node_modules', 'electron')
const extract = require(path.join(FRONTEND, 'node_modules', 'extract-zip'))
const { downloadArtifact } = require(path.join(FRONTEND, 'node_modules', '@electron', 'get'))
const checksums = require(path.join(ELECTRON_PKG, 'checksums.json'))

const t0 = Date.now()
const log = (...a) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1)}s]`, ...a)

setTimeout(() => {
  log('!! TIMEOUT：事件循环仍未结束（Promise 未 settle），强制退出')
  process.exit(2)
}, 120000)

async function main () {
  log('step1: downloadArtifact（走缓存）')
  const zipPath = await downloadArtifact({
    version: '30.5.1',
    artifactName: 'electron',
    checksums,
    platform: 'win32',
    arch: 'x64'
  })
  log('step1 done:', zipPath)

  const dist = path.join(ELECTRON_PKG, 'dist')
  fs.rmSync(dist, { recursive: true, force: true })

  log('step2: extract 到真实 dist（含中文路径）')
  let n = 0
  try {
    await extract(zipPath, {
      dir: dist,
      onEntry: e => {
        n++
        if (n <= 3 || n % 5 === 0) log('  entry', n, e.fileName)
      }
    })
    log(`step2 done，共处理 ${n} 个条目`)
  } catch (err) {
    log(`step2 FAILED，失败于第 ${n} 个条目之后：`, err && err.stack ? err.stack : String(err))
  }
  log('step2 dist 内容:', fs.existsSync(dist) ? fs.readdirSync(dist).join(', ') : '(dist 不存在)')
  log('step2 locales 内容:', fs.existsSync(path.join(dist, 'locales'))
    ? fs.readdirSync(path.join(dist, 'locales')).length + ' 个文件'
    : '(无 locales)')

  // step3: 相同 zip 解压到纯 ASCII 路径做对照
  const asciiDir = 'D:\\electron-probe-ascii-dist'
  fs.rmSync(asciiDir, { recursive: true, force: true })
  log('step3: extract 到 ASCII 路径', asciiDir)
  let m = 0
  try {
    await extract(zipPath, {
      dir: asciiDir,
      onEntry: e => {
        m++
        if (m <= 3 || m % 5 === 0) log('  entryA', m, e.fileName)
      }
    })
    log(`step3 done，共处理 ${m} 个条目`)
  } catch (err) {
    log(`step3 FAILED，失败于第 ${m} 个条目之后：`, err && err.stack ? err.stack : String(err))
  }
  log('step3 ascii 内容:', fs.existsSync(asciiDir) ? fs.readdirSync(asciiDir).join(', ') : '(目录不存在)')
}

main().then(
  () => { log('PROBE COMPLETE'); process.exit(0) },
  e => { log('PROBE UNEXPECTED ERROR', e && e.stack ? e.stack : e); process.exit(1) }
)
