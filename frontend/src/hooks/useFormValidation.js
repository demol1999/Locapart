import { useState } from 'react';

// Règles de validation
const validationRules = {
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    maxLength: 255,
    messages: {
      required: 'L\'email est requis',
      pattern: 'Format d\'email invalide',
      maxLength: 'L\'email ne peut pas dépasser 255 caractères'
    }
  },
  password: {
    required: true,
    minLength: 8,
    maxLength: 255,
    messages: {
      required: 'Le mot de passe est requis',
      minLength: 'Le mot de passe doit contenir au moins 8 caractères',
      maxLength: 'Le mot de passe ne peut pas dépasser 255 caractères'
    }
  },
  first_name: {
    required: true,
    maxLength: 100,
    messages: {
      required: 'Le prénom est requis',
      maxLength: 'Le prénom ne peut pas dépasser 100 caractères'
    }
  },
  last_name: {
    required: true,
    maxLength: 100,
    messages: {
      required: 'Le nom est requis',
      maxLength: 'Le nom ne peut pas dépasser 100 caractères'
    }
  },
  phone: {
    required: true,
    pattern: /^[0-9+\-\s\(\)]{10,20}$/,
    maxLength: 50,
    messages: {
      required: 'Le téléphone est requis',
      pattern: 'Format de téléphone invalide',
      maxLength: 'Le téléphone ne peut pas dépasser 50 caractères'
    }
  },
  street_number: {
    required: false,
    maxLength: 100,
    messages: {
      maxLength: 'Le numéro de rue ne peut pas dépasser 100 caractères'
    }
  },
  street_name: {
    required: false,
    maxLength: 500,
    messages: {
      maxLength: 'Le nom de rue ne peut pas dépasser 500 caractères'
    }
  },
  complement: {
    required: false,
    maxLength: 500,
    messages: {
      maxLength: 'Le complément d\'adresse ne peut pas dépasser 500 caractères'
    }
  },
  postal_code: {
    required: false,
    pattern: /^[0-9]{5}$/,
    maxLength: 50,
    messages: {
      pattern: 'Le code postal doit contenir 5 chiffres',
      maxLength: 'Le code postal ne peut pas dépasser 50 caractères'
    }
  },
  city: {
    required: false,
    maxLength: 200,
    messages: {
      maxLength: 'La ville ne peut pas dépasser 200 caractères'
    }
  },
  country: {
    required: false,
    maxLength: 200,
    messages: {
      maxLength: 'Le pays ne peut pas dépasser 200 caractères'
    }
  },
  // Building fields
  name: {
    required: true,
    maxLength: 255,
    messages: {
      required: 'Le nom de l\'immeuble est requis',
      maxLength: 'Le nom ne peut pas dépasser 255 caractères'
    }
  },
  floors: {
    required: true,
    min: 1,
    max: 200,
    messages: {
      required: 'Le nombre d\'étages est requis',
      min: 'Le nombre d\'étages doit être supérieur à 0',
      max: 'Le nombre d\'étages ne peut pas dépasser 200'
    }
  },
  // Apartment fields
  type_logement: {
    required: true,
    maxLength: 50,
    messages: {
      required: 'Le type de logement est requis',
      maxLength: 'Le type de logement ne peut pas dépasser 50 caractères'
    }
  },
  layout: {
    required: true,
    maxLength: 50,
    messages: {
      required: 'L\'agencement est requis',
      maxLength: 'L\'agencement ne peut pas dépasser 50 caractères'
    }
  },
  floor: {
    required: false,
    min: -5,
    max: 200,
    messages: {
      min: 'L\'étage ne peut pas être inférieur à -5',
      max: 'L\'étage ne peut pas dépasser 200'
    }
  }
};

// Fonction de validation d'un champ
const validateField = (fieldName, value, customRules = {}) => {
  const rules = { ...validationRules[fieldName], ...customRules };
  if (!rules) return null;

  const errors = [];

  // Vérification required
  if (rules.required && (!value || value.toString().trim() === '')) {
    errors.push(rules.messages.required);
  }

  // Si pas de valeur et pas required, pas d'autres validations
  if (!value || value.toString().trim() === '') {
    return errors.length > 0 ? errors : null;
  }

  const valueStr = value.toString();

  // Vérification pattern
  if (rules.pattern && !rules.pattern.test(valueStr)) {
    errors.push(rules.messages.pattern);
  }

  // Vérification maxLength
  if (rules.maxLength && valueStr.length > rules.maxLength) {
    errors.push(rules.messages.maxLength);
  }

  // Vérification minLength
  if (rules.minLength && valueStr.length < rules.minLength) {
    errors.push(rules.messages.minLength);
  }

  // Vérification min (pour les nombres)
  if (rules.min !== undefined) {
    const numValue = Number(value);
    if (!isNaN(numValue) && numValue < rules.min) {
      errors.push(rules.messages.min);
    }
  }

  // Vérification max (pour les nombres)
  if (rules.max !== undefined) {
    const numValue = Number(value);
    if (!isNaN(numValue) && numValue > rules.max) {
      errors.push(rules.messages.max);
    }
  }

  return errors.length > 0 ? errors : null;
};

// Hook de validation de formulaire
export const useFormValidation = (initialValues = {}, customValidationRules = {}) => {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  // Validation d'un champ spécifique
  const validateSingleField = (fieldName, value) => {
    const fieldErrors = validateField(fieldName, value, customValidationRules[fieldName]);
    setErrors(prev => ({
      ...prev,
      [fieldName]: fieldErrors
    }));
    return fieldErrors;
  };

  // Validation de confirmation de mot de passe
  const validatePasswordConfirmation = (password, confirmPassword) => {
    if (confirmPassword && password !== confirmPassword) {
      const error = ['Les mots de passe ne correspondent pas'];
      setErrors(prev => ({
        ...prev,
        passwordConfirm: error
      }));
      return error;
    } else {
      setErrors(prev => ({
        ...prev,
        passwordConfirm: null
      }));
      return null;
    }
  };

  // Validation de tous les champs
  const validateForm = (formValues = values) => {
    const newErrors = {};
    let isValid = true;

    Object.keys(formValues).forEach(fieldName => {
      if (fieldName === 'passwordConfirm') return; // Géré séparément
      
      const fieldErrors = validateField(fieldName, formValues[fieldName], customValidationRules[fieldName]);
      if (fieldErrors) {
        newErrors[fieldName] = fieldErrors;
        isValid = false;
      }
    });

    // Validation de confirmation de mot de passe si présente
    if (formValues.password && formValues.passwordConfirm !== undefined) {
      const confirmError = validatePasswordConfirmation(formValues.password, formValues.passwordConfirm);
      if (confirmError) {
        newErrors.passwordConfirm = confirmError;
        isValid = false;
      }
    }

    setErrors(newErrors);
    return isValid;
  };

  // Gestionnaire de changement de valeur
  const handleChange = (fieldName, value) => {
    setValues(prev => ({
      ...prev,
      [fieldName]: value
    }));

    // Validation en temps réel si le champ a été touché
    if (touched[fieldName]) {
      setTimeout(() => {
        validateSingleField(fieldName, value);
        
        // Validation spéciale pour confirmation de mot de passe
        if (fieldName === 'password' && values.passwordConfirm !== undefined) {
          validatePasswordConfirmation(value, values.passwordConfirm);
        }
        if (fieldName === 'passwordConfirm') {
          validatePasswordConfirmation(values.password, value);
        }
      }, 100);
    }
  };

  // Gestionnaire de focus sur un champ
  const handleBlur = (fieldName) => {
    setTouched(prev => ({
      ...prev,
      [fieldName]: true
    }));
    
    validateSingleField(fieldName, values[fieldName]);
    
    // Validation spéciale pour confirmation de mot de passe
    if (fieldName === 'passwordConfirm') {
      validatePasswordConfirmation(values.password, values[fieldName]);
    }
  };

  // Reset du formulaire
  const reset = () => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  };

  // Obtenir l'erreur d'un champ
  const getFieldError = (fieldName) => {
    return errors[fieldName] && touched[fieldName] ? errors[fieldName][0] : null;
  };

  // Vérifier si un champ a une erreur
  const hasFieldError = (fieldName) => {
    return !!(errors[fieldName] && touched[fieldName]);
  };

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    validateForm,
    validateSingleField,
    getFieldError,
    hasFieldError,
    reset,
    setValues
  };
};

export default useFormValidation;