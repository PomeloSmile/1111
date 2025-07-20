const { defineConfig } = require('@vue/cli-service')
const path = require('path')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 3000,
    proxy: {
      '^/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''
        },
        logLevel: 'debug'
      }
    }
  },
  configureWebpack: {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src')
      }
    },
    optimization: {
      minimize: process.env.NODE_ENV === 'production'
    }
  },
  chainWebpack: config => {
    // 移除废弃的util._extend警告
    config.plugin('define').tap(args => {
      args[0].__VUE_OPTIONS_API__ = true
      args[0].__VUE_PROD_DEVTOOLS__ = false
      return args
    })
  }
})
