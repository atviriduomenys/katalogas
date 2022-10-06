const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const webpack = require('webpack')

module.exports = {
  mode: "development",
  entry: path.resolve(__dirname, './src/index.js'),
  output: {
    path: path.resolve(__dirname, '../vitrina/static'),
    filename: 'js/bundle.js'
  },
  module: {
    rules: [{
      test: /\.scss$/,
      use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
          'sass-loader'
        ]
    },
    {
      test: /\.m?js$/,
      exclude: /(node_modules)/,
      loader: "babel-loader",
      options: {
         presets: ['@babel/preset-env']
      }
    },]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'css/adp-final.css'
    }),
    new webpack.ProvidePlugin({
      jQuery: 'jquery',
      $: 'jquery',
    })
  ],
};