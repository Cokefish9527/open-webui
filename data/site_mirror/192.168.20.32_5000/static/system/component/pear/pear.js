layui.config({
    base: '/static/system/component/pear/module/',
    version: '4.0.3'
}).extend({
    admin: 'admin',
    page: 'page',
    tabPage: 'tabPage',
    menu: 'menu',
    fullscreen: 'fullscreen',
    messageCenter: 'messageCenter',
    menuSearch: 'menuSearch',
    button: 'button',
    tools: 'tools',
    popup: 'extends/popup',
    count: 'extends/count',
    toast: 'extends/toast',
    nprogress: 'extends/nprogress',
    echarts: 'extends/echarts',
    echartsTheme: 'extends/echartsTheme',
    yaml: 'extends/yaml',
    dtree: 'dtree'
}).use([], function () { });