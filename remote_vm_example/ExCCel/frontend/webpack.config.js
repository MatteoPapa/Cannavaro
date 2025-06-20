/* eslint-disable @typescript-eslint/no-var-requires,no-undef */

const path = require('path')
const HtmlWebpackPlugin = require('html-webpack-plugin')

module.exports = {
  context: __dirname,
  entry: './src/index.tsx',
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(jpe?g|png|gif|svg|webp)$/i,
        type: 'asset/resource',
        generator: {
          filename: 'static/[name][ext]'
        }
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js'],
  },
  plugins: [
    new HtmlWebpackPlugin({
      filename: 'index.html',
      template: path.join(__dirname, 'public', 'index.html'),
    })
  ],
  devServer: {
    port: 8000,
    historyApiFallback: true,
    proxy: {
      context: '/api',
      target: 'http://127.0.0.1:5000',
    }
  },
  watchOptions: {
    ignored: /node_modules/
  },
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
    publicPath: '/'
  }
}