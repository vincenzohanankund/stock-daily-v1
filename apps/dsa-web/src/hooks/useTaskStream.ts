import { useEffect, useRef, useCallback } from 'react';
import { analysisApi } from '../api/analysis';
import type { TaskInfo } from '../types/analysis';
import { fetchEventSource, EventStreamContentType } from '@microsoft/fetch-event-source';

/**
 * SSE 事件类型
 */
export type SSEEventType =
  | 'connected'
  | 'task_created'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'heartbeat';

/**
 * SSE 事件数据
 */
export interface SSEEvent {
  type: SSEEventType;
  task?: TaskInfo;
  timestamp?: string;
}

/**
 * SSE Hook 配置
 */
export interface UseTaskStreamOptions {
  /** 任务创建回调 */
  onTaskCreated?: (task: TaskInfo) => void;
  /** 任务开始回调 */
  onTaskStarted?: (task: TaskInfo) => void;
  /** 任务完成回调 */
  onTaskCompleted?: (task: TaskInfo) => void;
  /** 任务失败回调 */
  onTaskFailed?: (task: TaskInfo) => void;
  /** 连接成功回调 */
  onConnected?: () => void;
  /** 连接错误回调 */
  onError?: (error: Error | Event) => void;
  /** 是否自动重连 */
  autoReconnect?: boolean;
  /** 重连延迟(ms) */
  reconnectDelay?: number;
  /** 是否启用 */
  enabled?: boolean;
}

/**
 * SSE Hook 返回值
 */
export interface UseTaskStreamResult {
  /** 是否已连接 */
  isConnected: boolean;
  /** 手动重连 */
  reconnect: () => void;
  /** 手动断开 */
  disconnect: () => void;
}

/**
 * 任务流 SSE Hook
 * 用于接收实时任务状态更新
 *
 * @example
 * ```tsx
 * const { isConnected } = useTaskStream({
 *   onTaskCompleted: (task) => {
 *     console.log('Task completed:', task);
 *     refreshHistory();
 *   },
 *   onTaskFailed: (task) => {
 *     showError(task.error);
 *   },
 * });
 * ```
 */
export function useTaskStream(options: UseTaskStreamOptions = {}): UseTaskStreamResult {
  const {
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskFailed,
    onConnected,
    onError,
    autoReconnect = true,
    enabled = true,
  } = options;

  const controllerRef = useRef<AbortController | null>(null);
  const isConnectedRef = useRef(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 使用 ref 存储回调，避免 SSE 连接因回调变化而频繁重连
  const callbacksRef = useRef({
    onTaskCreated,
    onTaskStarted,
    onTaskCompleted,
    onTaskFailed,
    onConnected,
    onError,
  });

  // 每次渲染时更新回调 ref（确保事件处理使用最新回调）
  useEffect(() => {
    callbacksRef.current = {
      onTaskCreated,
      onTaskStarted,
      onTaskCompleted,
      onTaskFailed,
      onConnected,
      onError,
    };
  });

  // 将 snake_case 转换为 camelCase
  const toCamelCase = (data: Record<string, unknown>): TaskInfo => {
    return {
      taskId: data.task_id as string,
      stockCode: data.stock_code as string,
      stockName: data.stock_name as string | undefined,
      status: data.status as TaskInfo['status'],
      progress: data.progress as number,
      message: data.message as string | undefined,
      reportType: data.report_type as string,
      createdAt: data.created_at as string,
      startedAt: data.started_at as string | undefined,
      completedAt: data.completed_at as string | undefined,
      error: data.error as string | undefined,
    };
  };

  // 解析 SSE 数据
  const parseEventData = useCallback((eventData: string): TaskInfo | null => {
    try {
      const data = JSON.parse(eventData);
      return toCamelCase(data);
    } catch (e) {
      console.error('Failed to parse SSE event data:', e);
      return null;
    }
  }, []);

  // Ref to hold the connect function to break circular dependency
  const connectRef = useRef<() => void>(() => {});

  // 断开连接
  const disconnect = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    isConnectedRef.current = false;
  }, []);

  // 创建 EventSource 连接
  const connect = useCallback(() => {
    disconnect();

    const controller = new AbortController();
    controllerRef.current = controller;

    const url = analysisApi.getTaskStreamUrl();
    const token = localStorage.getItem('auth_token');
    
    const headers: Record<string, string> = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    fetchEventSource(url, {
        method: 'GET',
        headers: headers,
        signal: controller.signal,
        async onopen(response) {
            if (response.ok && response.headers.get('content-type')?.includes(EventStreamContentType)) {
                isConnectedRef.current = true;
                callbacksRef.current.onConnected?.();
                return; 
            } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                 if (response.status === 401) {
                     throw new Error('Unauthorized');
                 }
                 throw new Error(`Failed to connect: ${response.statusText}`);
            }
        },
        onmessage(msg) {
            if (msg.event === 'heartbeat' || msg.event === 'connected') return;

            const task = parseEventData(msg.data);
            if (task) {
                switch (msg.event) {
                    case 'task_created':
                        callbacksRef.current.onTaskCreated?.(task);
                        break;
                    case 'task_started':
                        callbacksRef.current.onTaskStarted?.(task);
                        break;
                    case 'task_completed':
                        callbacksRef.current.onTaskCompleted?.(task);
                        break;
                    case 'task_failed':
                        callbacksRef.current.onTaskFailed?.(task);
                        break;
                }
            }
        },
        onerror(err) {
            isConnectedRef.current = false;
            callbacksRef.current.onError?.(err instanceof Error ? err : new Error(String(err)));
            
            if (err instanceof Error && err.message === 'Unauthorized') {
                throw err;
            }
            
            if (autoReconnect && enabled) {
                // Do nothing -> Retry
            } else {
                throw err;
            }
        }
    }).catch(err => {
        console.error('SSE connection failed', err);
        isConnectedRef.current = false;
    });

  }, [autoReconnect, enabled, parseEventData, disconnect]);

  // Update connectRef whenever connect changes
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // 重连
  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [disconnect, connect]);

  // 启用/禁用时连接/断开
  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected: isConnectedRef.current,
    reconnect,
    disconnect,
  };
}

export default useTaskStream;
