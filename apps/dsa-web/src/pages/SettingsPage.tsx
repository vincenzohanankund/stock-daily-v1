import React, { useEffect } from 'react';
import { Save, RefreshCw, Info, Settings, ChevronRight } from 'lucide-react';
import { useSystemConfig } from '../hooks';
import { getCategoryDescriptionZh, getCategoryTitleZh, getFieldTitleZh, getFieldDescriptionZh } from '../utils/systemConfigI18n';
import type { SystemConfigItem, SystemConfigFieldSchema, SystemConfigCategory } from '../types/systemConfig';

import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Select } from '../components/common/Select';
import { Switch } from '../components/common/Switch';
import { Tooltip } from '../components/common/Tooltip';
import { Label } from '../components/common/Label';
import { Spinner } from '../components/common/Spinner';
import { useToast } from '../components/common/Toast';

const SettingsPage: React.FC = () => {
  const {
    categories,
    itemsByCategory,
    activeCategory,
    setActiveCategory,
    hasDirty,
    dirtyCount,
    isLoading,
    isSaving,
    loadError,
    saveError,
    load,
    save,
    setDraftValue,
    draftValues
  } = useSystemConfig();

  const toast = useToast();

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (loadError) toast.error(loadError);
    if (saveError) toast.error(saveError);
  }, [loadError, saveError, toast]);

  const activeItems = itemsByCategory[activeCategory] || [];

  const renderField = (item: SystemConfigItem) => {
    const schema = (item.schema || {}) as SystemConfigFieldSchema;
    const controlType = schema.uiControl || 'text';
    const isEditable = schema.isEditable !== false;
    const currentValue = draftValues[item.key] !== undefined ? draftValues[item.key] : item.value;
    const description = getFieldDescriptionZh(item.key) || schema.description;
    const title = getFieldTitleZh(item.key) || item.key;

    const handleChange = (val: any) => {
      setDraftValue(item.key, String(val));
    };

    let inputNode;
    if (controlType === 'switch') {
      inputNode = (
        <div className="flex items-center space-x-2">
            <Switch
            checked={currentValue === 'true'}
            onChange={(checked) => handleChange(checked)}
            disabled={!isEditable}
            />
            <span className="text-sm text-muted-foreground">{currentValue === 'true' ? '已启用' : '已禁用'}</span>
        </div>
      );
    } else if (controlType === 'select' && schema.options) {
      inputNode = (
        <Select
          value={currentValue}
          onChange={handleChange}
          options={schema.options.map(opt => ({ value: opt, label: opt }))}
          disabled={!isEditable}
          className="w-full sm:w-[300px]"
        />
      );
    } else if (controlType === 'textarea') {
      inputNode = (
        <textarea
          value={currentValue}
          onChange={(e) => handleChange(e.target.value)}
          disabled={!isEditable}
          rows={4}
          className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 resize-y"
        />
      );
    } else if (controlType === 'password') {
      inputNode = (
        <Input
          type="password"
          value={currentValue}
          onChange={(e) => handleChange(e.target.value)}
          disabled={!isEditable}
          className="max-w-md"
        />
      );
    } else {
      inputNode = (
        <Input
          value={currentValue}
          onChange={(e) => handleChange(e.target.value)}
          disabled={!isEditable}
          className="max-w-md"
        />
      );
    }

    return (
      <div key={item.key} className="space-y-3 pt-4 first:pt-0">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <Label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {title}
            </Label>
            {description && (
              <Tooltip content={description}>
                <Info size={14} className="text-muted-foreground/70 cursor-help hover:text-foreground transition-colors" />
              </Tooltip>
            )}
          </div>
          {description && <p className="text-[13px] text-muted-foreground leading-relaxed">{description}</p>}
        </div>
        {inputNode}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col p-6 bg-background">
      <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">系统设置</h1>
            <p className="text-sm text-muted-foreground mt-1">管理应用配置和偏好设置。</p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => load()} disabled={isLoading || isSaving}>
              <RefreshCw size={16} className="mr-2" />
              重置
            </Button>
            <Button
              variant="primary"
              onClick={() => save()}
              disabled={!hasDirty || isSaving || isLoading}
              loading={isSaving}
            >
              <Save size={16} className="mr-2" />
              保存修改 {dirtyCount > 0 && `(${dirtyCount})`}
            </Button>
          </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-sm">
        {isLoading ? (
          <div className="w-full h-full flex flex-col justify-center items-center gap-3">
            <Spinner size="lg" />
            <span className="text-muted-foreground">正在加载配置...</span>
          </div>
        ) : (
          <>
            {/* Sidebar */}
            <div className="w-full lg:w-64 border-b lg:border-b-0 lg:border-r border-border bg-muted/30 overflow-y-auto custom-scrollbar">
              <nav className="flex flex-col p-3 gap-1">
                {categories.map((cat) => (
                  <button
                    key={cat.category}
                    onClick={() => setActiveCategory(cat.category)}
                    className={`
                      group flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-all duration-200
                      ${activeCategory === cat.category 
                        ? 'bg-background text-foreground shadow-sm ring-1 ring-border' 
                        : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'}
                    `}
                  >
                    <div className="flex items-center gap-2">
                        <Settings size={16} className={`opacity-70 ${activeCategory === cat.category ? 'text-primary' : ''}`} />
                        {getCategoryTitleZh(cat.category)}
                    </div>
                    {activeCategory === cat.category && <ChevronRight size={14} className="text-muted-foreground" />}
                  </button>
                ))}
              </nav>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto bg-card custom-scrollbar">
              <div className="max-w-3xl p-6 lg:p-8 space-y-8">
                <div className="pb-4 border-b border-border">
                  <h3 className="text-lg font-semibold leading-none tracking-tight mb-2">
                    {getCategoryTitleZh(activeCategory as SystemConfigCategory)}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {getCategoryDescriptionZh(activeCategory as SystemConfigCategory)}
                  </p>
                </div>
                
                <div className="space-y-8">
                  {activeItems.map((item) => renderField(item))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;
