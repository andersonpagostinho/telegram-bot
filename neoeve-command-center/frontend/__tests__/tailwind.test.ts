import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

describe('Tailwind CSS Configuration', () => {
  const projectRoot = join(__dirname, '..');

  it('should have tailwind.config.ts', () => {
    const path = join(projectRoot, 'tailwind.config.ts');
    expect(existsSync(path)).toBe(true);
    const content = readFileSync(path, 'utf-8');
    expect(content).toContain('darkMode');
    expect(content).toContain('content');
  });

  it('should have postcss.config.cjs', () => {
    const path = join(projectRoot, 'postcss.config.cjs');
    expect(existsSync(path)).toBe(true);
    const content = readFileSync(path, 'utf-8');
    expect(content).toContain('tailwindcss');
    expect(content).toContain('autoprefixer');
  });

  it('should have Tailwind directives in src/main.css', () => {
    const path = join(projectRoot, 'src', 'main.css');
    expect(existsSync(path)).toBe(true);
    const content = readFileSync(path, 'utf-8');
    expect(content).toContain('@tailwind base');
    expect(content).toContain('@tailwind components');
    expect(content).toContain('@tailwind utilities');
  });

  it('App.tsx should use Tailwind classes', () => {
    const path = join(projectRoot, 'src', 'App.tsx');
    const content = readFileSync(path, 'utf-8');
    expect(content).toContain('className');
    expect(content).toMatch(/className=".*(slate-900|bg-|text-)/);
  });

  it('should have dark mode configured in tailwind config', () => {
    const path = join(projectRoot, 'tailwind.config.ts');
    const content = readFileSync(path, 'utf-8');
    expect(content).toContain('darkMode: "class"');
  });
});
