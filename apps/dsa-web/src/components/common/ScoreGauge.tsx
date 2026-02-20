import type React from 'react';
import { getSentimentLabel } from '../../types/analysis';

interface ScoreGaugeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

/**
 * 情绪评分仪表盘 - 发光环形进度条
 * 参考金融终端风格设计，带过渡动画
 */
export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  score,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  const label = getSentimentLabel(score);

  // 尺寸配置
  const sizeConfig = {
    sm: { width: 100, stroke: 8, fontSize: 'text-2xl', labelSize: 'text-xs', gap: 6 },
    md: { width: 140, stroke: 10, fontSize: 'text-4xl', labelSize: 'text-sm', gap: 8 },
    lg: { width: 180, stroke: 12, fontSize: 'text-5xl', labelSize: 'text-base', gap: 10 },
  };

  const { width, stroke, fontSize, labelSize } = sizeConfig[size];
  const radius = (width - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  
  // 240度圆弧 (2/3 圆)
  // 起始角度 150度 (左下)，结束角度 30度 (右下)，顺时针
  // 这里使用 strokeDasharray 来控制显示的弧长
  // 总长度是 circumference
  // 我们显示 240/360 = 2/3 = 0.666...
  const visibleFraction = 240 / 360;
  const visibleLength = circumference * visibleFraction;
  
  // 旋转 -210度 (或者 150度) 来调整开口位置
  // SVG 圆的起点 (0度) 是 3点钟方向 (右)
  // 我们想要开口在下方 (90度方向是下)
  // 如果我们要开口在下方 120度范围 (240度圆弧)
  // 那么圆弧应该从 150度 (左下) 到 30度 (右下)
  // 0度在右边。
  // 旋转 150度: 起点变到 150度位置。
  const rotation = 150; 

  // 颜色映射
  const getStrokeColor = (s: number) => {
    if (s >= 60) return '#22c55e'; // green-500
    if (s >= 40) return '#eab308'; // yellow-500
    return '#ef4444'; // red-500
  };

  const strokeColor = getStrokeColor(score);

  return (
    <div className={`flex flex-col items-center relative ${className}`}>
      {/* Title moved to top as requested */}
      {showLabel && (
        <span className="uppercase text-[10px] font-semibold tracking-wider text-muted-foreground/70 mb-2">
          恐慌与贪婪指数
        </span>
      )}
      
      <div className="relative" style={{ width, height: width * 0.85 }}> {/* Slightly reduced height for bottom cut */}
        <svg 
          className="overflow-visible" 
          width={width} 
          height={width}
          viewBox={`0 0 ${width} ${width}`}
        >
          <defs>
            <linearGradient id={`gauge-gradient-${score}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={strokeColor} stopOpacity="0.6" />
              <stop offset="100%" stopColor={strokeColor} stopOpacity="1" />
            </linearGradient>
            <filter id={`gauge-glow-${score}`} x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="4" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Background Track */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke="var(--color-muted)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${visibleLength} ${circumference}`}
            strokeDashoffset={0}
            transform={`rotate(${rotation} ${width / 2} ${width / 2})`}
            className="opacity-20"
          />

          {/* Progress Arc */}
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${visibleLength} ${circumference}`}
            strokeDashoffset={visibleLength * (1 - score / 100)}
            transform={`rotate(${rotation} ${width / 2} ${width / 2})`}
            filter={`url(#gauge-glow-${score})`}
            className="transition-all duration-1000 ease-out"
            style={{ 
              transition: 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          />
        </svg>

        {/* Center Score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
          <span className={`font-bold ${fontSize} transition-colors duration-500`} style={{ color: strokeColor }}>
            {Math.round(score)}
          </span>
          <span className={`font-medium text-muted-foreground ${labelSize} mt-1`}>
            {label}
          </span>
        </div>
      </div>
    </div>
  );
};
