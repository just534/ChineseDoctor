<template>
  <div class="status-page">
    <span class="seal big">禁</span>
    <h2 class="kai">无权访问</h2>
    <p>您的账号暂无访问此页面的权限，如需开通请联系管理员。</p>
    <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
  </div>
</template>

<style scoped lang="scss">
.status-page { text-align: center; padding: 100px 20px; h2 { font-size: 30px; letter-spacing: 6px; margin: 20px 0 8px; } p { color: var(--ink-3); } }
.big { width: 80px; height: 80px; font-size: 42px; transform: rotate(-6deg); }
</style>
