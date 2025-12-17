module.exports = {
  style: {
    postcss: {
      loaderOptions: {
        postcssOptions: {
          plugins: [],
        },
      },
    },
  },
  devServer: (devServerConfig) => {
    devServerConfig.allowedHosts = "all";
    return devServerConfig;
  },
};
