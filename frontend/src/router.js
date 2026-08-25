import { createRouter, createWebHistory } from 'vue-router'
import SubscriptionsView from './views/SubscriptionsView.vue'
import HostsView from './views/HostsView.vue'
import ChannelsView from './views/ChannelsView.vue'

const routes = [
  { path: '/', redirect: '/subscriptions' },
  { path: '/subscriptions', name: 'subscriptions', component: SubscriptionsView },
  { path: '/channels', name: 'channels', component: ChannelsView },
  { path: '/hosts', name: 'hosts', component: HostsView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
