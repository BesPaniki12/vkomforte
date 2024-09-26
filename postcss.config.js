module.exports = {
    map: false,  // Отключаем использование source map
    plugins: {
        'postcss-modules': {
            generateScopedName: '[name]__[local]___[hash:base64:5]',
        },
        'autoprefixer': {},
        'cssnano': {
            preset: 'default',
        },
    },
};
