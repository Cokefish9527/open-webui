// HSAI任务状态管理存储

import { writable, type Writable } from 'svelte/store';
import type { HSAITask, HSAITaskStep } from '$lib/types/message';

// 当前活动任务
export const activeTask: Writable<HSAITask | null> = writable(null);

// 任务步骤
export const taskSteps: Writable<HSAITaskStep[]> = writable([]);

// 任务列表
export const taskList: Writable<HSAITask[]> = writable([]);

// 更新活动任务
export function setActiveTask(task: HSAITask | null): void {
	activeTask.set(task);
}

// 更新任务步骤
export function setTaskSteps(steps: HSAITaskStep[]): void {
	taskSteps.set(steps);
}

// 添加任务步骤
export function addTaskStep(step: HSAITaskStep): void {
	taskSteps.update(steps => [...steps, step]);
}

// 更新任务列表
export function setTaskList(tasks: HSAITask[]): void {
	taskList.set(tasks);
}

// 添加任务到列表
export function addTask(task: HSAITask): void {
	taskList.update(tasks => [...tasks, task]);
}

// 更新任务列表中的特定任务
export function updateTaskInList(updatedTask: HSAITask): void {
	taskList.update(tasks => 
		tasks.map(task => task.id === updatedTask.id ? updatedTask : task)
	);
}

// 从任务列表中移除任务
export function removeTaskFromList(taskId: string): void {
	taskList.update(tasks => tasks.filter(task => task.id !== taskId));
}