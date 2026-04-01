const axios = require("axios");

function createHttpClient(baseURL) {
  return axios.create({
    baseURL,
    timeout: 5000
  });
}

module.exports = { createHttpClient };
