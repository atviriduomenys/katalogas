const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const webpack = require('webpack')

module.exports = {
  mode: "development",
  entry: {
    bundle: path.resolve(__dirname, './src/index.js'),
    jquery: path.resolve(__dirname, './src/jquery.js'),
  },
  output: {
    path: path.resolve(__dirname, '../vitrina/static'),
    filename: 'js/[name].js',
    library: '[name]'
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
      filename: 'css/bundle.css'
    }),
    new webpack.ProvidePlugin({
      jQuery: 'jquery',
      $: 'jquery',
    })
  ],
  resolve: {
    alias: {
      images: path.resolve(__dirname, '../vitrina/static/img/'),
      fonts: path.resolve(__dirname, 'src/fonts/'),
    },
     modules: [path.resolve(__dirname, '../var/static/'), path.resolve(__dirname, 'node_modules')],
  },
};
