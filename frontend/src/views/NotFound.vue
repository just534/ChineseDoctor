<template>
  <div class="status-page">
    <span class="seal big">迷</span>
    <h2 class="kai">此路不通</h2>
    <p>您要找的页面不存在，或已被移走。</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped lang="scss">
.status-page { min-height: 100vh; text-align: center; padding: 120px 20px; h2 { font-size: 30px; letter-spacing: 6px; margin: 20px 0 8px; } p { color: var(--ink-3); } }
.big { width: 80px; height: 80px; font-size: 42px; transform: rotate(-6deg); }
</style>
