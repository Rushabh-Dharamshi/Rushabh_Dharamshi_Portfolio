module.exports = {
  default: {
    paths: ["tests/bdd/features/**/*.feature"],
    require: ["tests/bdd/steps/**/*.js"],
    format: ["progress"],
  },
};

