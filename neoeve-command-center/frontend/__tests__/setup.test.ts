import { describe, it, expect } from 'vitest';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

describe('Frontend Foundation Setup', () => {
  const projectRoot = join(__dirname, '..');

  it('should have package.json with required dependencies', () => {
    const packagePath = join(projectRoot, 'package.json');
    expect(existsSync(packagePath)).toBe(true);

    const pkg = JSON.parse(readFileSync(packagePath, 'utf-8'));

    // Required dependencies
    expect(pkg.dependencies).toHaveProperty('react', '^18.2.0');
    expect(pkg.dependencies).toHaveProperty('react-dom', '^18.2.0');
    expect(pkg.dependencies).toHaveProperty('react-router-dom', '^6.20.0');
    expect(pkg.dependencies).toHaveProperty('@tanstack/react-query', '^5.28.0');
    expect(pkg.dependencies).toHaveProperty('zustand', '^4.4.0');
    expect(pkg.dependencies).toHaveProperty('axios', '^1.6.0');

    // Required scripts
    expect(pkg.scripts).toHaveProperty('dev');
    expect(pkg.scripts).toHaveProperty('build');
    expect(pkg.scripts).toHaveProperty('test');
  });

  it('should have TypeScript configuration with strict mode', () => {
    const tsPath = join(projectRoot, 'tsconfig.json');
    expect(existsSync(tsPath)).toBe(true);

    const ts = JSON.parse(readFileSync(tsPath, 'utf-8'));
    expect(ts.compilerOptions.strict).toBe(true);
    expect(ts.compilerOptions.jsx).toBe('react-jsx');
  });

  it('should have Vite configuration', () => {
    const vitePath = join(projectRoot, 'vite.config.ts');
    expect(existsSync(vitePath)).toBe(true);
  });

  it('should have index.html entry point', () => {
    const indexPath = join(projectRoot, 'index.html');
    expect(existsSync(indexPath)).toBe(true);

    const html = readFileSync(indexPath, 'utf-8');
    expect(html).toContain('id="root"');
    expect(html).toContain('src/index.tsx');
  });

  it('should have React root at src/index.tsx', () => {
    const reactPath = join(projectRoot, 'src', 'index.tsx');
    expect(existsSync(reactPath)).toBe(true);

    const content = readFileSync(reactPath, 'utf-8');
    expect(content).toContain('React');
    expect(content).toContain('ReactDOM');
  });

  it('should have .env.example template', () => {
    const envPath = join(projectRoot, '.env.example');
    expect(existsSync(envPath)).toBe(true);
  });
});
