import React from 'react';
import { cn } from '../lib/utils';
import { Input } from './ui/input';
import { Label } from './ui/label';

// Interface Segregation: Séparation des responsabilités du FormInput
const FormInput = ({
  label,
  name,
  type = 'text',
  value,
  onChange,
  onBlur,
  error,
  required = false,
  placeholder = '',
  className = '',
  disabled = false,
  min,
  max,
  step,
  accept,
  ...props
}) => {
  const handleChange = (e) => {
    const newValue = type === 'number' ? e.target.value : e.target.value;
    onChange(name, newValue);
  };

  const handleBlur = () => {
    if (onBlur) {
      onBlur(name);
    }
  };

  return (
    <div className="space-y-2">
      {label && (
        <Label htmlFor={name} className="text-sm font-medium">
          {label}
          {required && (
            <span className="text-destructive ml-1" aria-label="Obligatoire">
              *
            </span>
          )}
        </Label>
      )}
      
      <Input
        id={name}
        name={name}
        type={type}
        value={value || ''}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        className={cn(
          error && "border-destructive focus-visible:ring-destructive",
          className
        )}
        disabled={disabled}
        min={min}
        max={max}
        step={step}
        accept={accept}
        aria-invalid={error ? 'true' : 'false'}
        aria-describedby={error ? `${name}-error` : undefined}
        {...props}
      />
      
      {error && (
        <p 
          id={`${name}-error`}
          className="text-sm text-destructive animate-fadeIn"
          role="alert"
        >
          {error}
        </p>
      )}
    </div>
  );
};

export default FormInput;