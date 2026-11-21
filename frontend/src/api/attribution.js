import {request,post} from './client.js';
export const projects={
  list:()=>request('/projects'),
  create:x=>post('/projects',x),
  events:id=>request(`/projects/${id}/events`),
  addEvent:(id,x)=>post(`/projects/${id}/events`,x),
  batch:(id,events)=>post(`/projects/${id}/events/batch`,{events}),
  withdraw:(id,x)=>post(`/projects/${id}/events/withdraw`,x),
  runs:id=>request(`/projects/${id}/runs`),
  recalc:id=>post(`/projects/${id}/runs`,{}),
  current:id=>request(`/projects/${id}/current`),
};
export const runs={list:()=>request('/runs'),get:id=>request(`/runs/${id}`)};
export const audits={list:()=>request('/audits')};
export const overview=()=>request('/overview');
