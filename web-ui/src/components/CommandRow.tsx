import React from 'react';
import TimingWidget from './TimingWidget';
import './CommandRow.css';

export interface CommandDef {
  id: string; // uuid local pour React key
  type: string;
  args: Record<string, any>;
}

interface ArgDef {
  name: string;
  type: string;
  label: string;
  required?: boolean;
  multiple?: boolean;
  min?: number;
  max?: number;
}

interface SchemaDef {
  label: string;
  icon: string;
  args: ArgDef[];
}

interface Props {
  cmd: CommandDef;
  schema: Record<string, SchemaDef>;
  index: number;
  total: number;
  onChange: (cmd: CommandDef) => void;
  onMove: (from: number, to: number) => void;
  onDelete: (id: string) => void;
}

const COMMAND_TYPES = ['vote', 'submit', 'turbo', 'boost', 'revote', 'swap', 'unlocked_boost', 'cancel'];

const CommandRow: React.FC<Props> = ({ cmd, schema, index, total, onChange, onMove, onDelete }) => {
  const def: SchemaDef | undefined = schema[cmd.type];

  const setArg = (name: string, value: any) => {
    onChange({ ...cmd, args: { ...cmd.args, [name]: value } });
  };

  const setType = (newType: string) => {
    // Peupler les args avec les valeurs par défaut du nouveau type
    const newDef: SchemaDef | undefined = schema[newType];
    const defaults: Record<string, any> = {};
    if (newDef) {
      for (const arg of newDef.args) {
        if (arg.type === 'timing') defaults[arg.name] = 'now';
        else if (arg.type === 'integer') defaults[arg.name] = arg.min ?? 1;
        else if (arg.type === 'condition') defaults[arg.name] = '<50';
        else if (arg.type === 'turbo_index') defaults[arg.name] = undefined;
        else if (arg.type === 'photo_list') defaults[arg.name] = [];
        // photo_uid, autres : undefined
      }
    }
    onChange({ ...cmd, type: newType, args: defaults });
  };

  const renderArg = (arg: ArgDef) => {
    const val = cmd.args[arg.name];

    if (arg.type === 'timing') {
      return (
        <span className="cmd-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <TimingWidget
            value={val ?? 'now'}
            onChange={v => setArg(arg.name, v)}
          />
        </span>
      );
    }

    if (arg.type === 'integer') {
      return (
        <span className="cmd-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <input
            type="number"
            className="arg-int"
            min={arg.min ?? 0}
            max={arg.max ?? 9999}
            value={val ?? ''}
            onChange={e => setArg(arg.name, e.target.value === '' ? undefined : +e.target.value)}
          />
        </span>
      );
    }

    if (arg.type === 'condition') {
      // "<50" → operator "<" + number 50
      const op = (val ?? '<').charAt(0) === '<' ? '<' : '>';
      const num = val ? parseInt(val.slice(1)) || 50 : 50;
      return (
        <span className="cmd-arg condition-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <select
            className="arg-op"
            value={op}
            onChange={e => setArg(arg.name, `${e.target.value}${num}`)}
          >
            <option value="<">&lt;</option>
            <option value=">">&gt;</option>
          </select>
          <input
            type="number"
            className="arg-int arg-pct"
            min={0} max={100}
            value={num}
            onChange={e => setArg(arg.name, `${op}${e.target.value}`)}
          />
          <span className="arg-pct-symbol">%</span>
        </span>
      );
    }

    if (arg.type === 'turbo_index') {
      return (
        <span className="cmd-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <select
            className="arg-select"
            value={val ?? ''}
            onChange={e => setArg(arg.name, e.target.value || undefined)}
          >
            <option value="">auto</option>
            <option value="[0]">photo 1</option>
            <option value="[1]">photo 2</option>
            <option value="[2]">photo 3</option>
          </select>
        </span>
      );
    }

    if (arg.type === 'photo_list') {
      const list: string[] = Array.isArray(val) ? val : [];
      return (
        <span className="cmd-arg photo-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <textarea
            className="arg-photos"
            rows={2}
            placeholder="UID1, UID2, ..."
            value={list.join(', ')}
            onChange={e => setArg(arg.name, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
          />
        </span>
      );
    }

    if (arg.type === 'photo_uid') {
      return (
        <span className="cmd-arg" key={arg.name} title={arg.label}>
          <span className="arg-label">{arg.label}</span>
          <input
            type="text"
            className="arg-uid"
            placeholder="UID"
            value={val ?? ''}
            onChange={e => setArg(arg.name, e.target.value || undefined)}
          />
        </span>
      );
    }

    return (
      <span className="cmd-arg" key={arg.name} title={arg.label}>
        <span className="arg-label">{arg.label}</span>
        <input
          type="text"
          className="arg-text"
          value={val ?? ''}
          onChange={e => setArg(arg.name, e.target.value || undefined)}
        />
      </span>
    );
  };

  return (
    <div className="cmd-row">
      <span className="cmd-controls">
        <button className="cmd-btn move-btn" disabled={index === 0} onClick={() => onMove(index, index - 1)} title="Monter">↑</button>
        <button className="cmd-btn move-btn" disabled={index === total - 1} onClick={() => onMove(index, index + 1)} title="Descendre">↓</button>
      </span>

      <span className="cmd-icon">{def?.icon ?? '❓'}</span>

      <select
        className="cmd-type-select"
        value={cmd.type}
        onChange={e => setType(e.target.value)}
      >
        {COMMAND_TYPES.map(t => (
          <option key={t} value={t}>
            {schema[t]?.icon ?? ''} {schema[t]?.label ?? t}
          </option>
        ))}
      </select>

      <span className="cmd-args">
        {def?.args.map(renderArg)}
      </span>

      <button className="cmd-btn delete-btn" onClick={() => onDelete(cmd.id)} title="Supprimer">🗑</button>
    </div>
  );
};

export default CommandRow;
