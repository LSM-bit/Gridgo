import {
  defineConfig,
  presetUno,
  presetAttributify,
} from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
  ],
  shortcuts: {
    'flex-center': 'flex items-center justify-center',
    'flex-between': 'flex items-center justify-between',
    'flex-col-center': 'flex flex-col items-center justify-center',
  },
  theme: {
    colors: {
      primary: '#409eff',
      success: '#67c23a',
      warning: '#e6a23c',
      danger: '#f56c6c',
      info: '#909399',
    },
  },
})
