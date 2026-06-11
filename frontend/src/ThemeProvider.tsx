import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { SKINS, loadSkin, type SkinKey } from './theme'
import { api } from './api'

interface ThemeCtx { skin: SkinKey; setSkin: (s: SkinKey) => void }
const Ctx = createContext<ThemeCtx>({ skin: 'song', setSkin: () => {} })
export const useSkin = () => useContext(Ctx)

function applySkin(key: SkinKey) {
  const skin = SKINS[key]
  const root = document.documentElement
  for (const [k, v] of Object.entries(skin.vars)) root.style.setProperty(k, v)
  root.setAttribute('data-skin', key)
  document.body.style.background = skin.vars['--ths-bg']
  document.body.style.color = skin.vars['--ths-text']
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [skin, setSkinState] = useState<SkinKey>(loadSkin)

  useEffect(() => { applySkin(skin) }, [skin])

  // 本地未选过主题时，采用机构默认主题
  useEffect(() => {
    if (localStorage.getItem('skin')) return
    api.get('/settings/theme')
      .then((r) => { if (SKINS[r.data.skin as SkinKey]) setSkinState(r.data.skin) })
      .catch(() => {})
  }, [])

  const setSkin = (s: SkinKey) => {
    localStorage.setItem('skin', s)
    setSkinState(s)
    // 同步为机构默认主题（已登录时）；失败不影响本地切换
    if (localStorage.getItem('token')) {
      api.put('/settings/theme', { skin: s }).catch(() => {})
    }
  }

  return (
    <Ctx.Provider value={{ skin, setSkin }}>
      <ConfigProvider locale={zhCN} theme={SKINS[skin].antd}>
        {children}
      </ConfigProvider>
    </Ctx.Provider>
  )
}
