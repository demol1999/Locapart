import React from 'react';
import { useTranslation } from 'react-i18next';
import { MapPin, Building2, Users } from 'lucide-react';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

// Dependency Inversion: Dépend d'abstractions (props) plutôt que de détails
export default function BuildingCard({ building, onClick, onEdit }) {
  const { t } = useTranslation();

  // Single Responsibility: Formatage de l'adresse
  const formatAddress = () => {
    const parts = [
      building.street_number,
      building.street_name,
      building.complement,
    ].filter(Boolean);
    
    return parts.join(' ');
  };

  const formatLocation = () => {
    const parts = [
      building.postal_code,
      building.city,
      building.country,
    ].filter(Boolean);
    
    return parts.join(' ');
  };

  return (
    <Card className="hover:shadow-lg transition-all duration-300 hover:scale-[1.02] cursor-pointer">
      <CardHeader className="pb-4" onClick={onClick}>
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            {building.name}
          </CardTitle>
          <Badge variant={building.is_copro ? "default" : "secondary"}>
            {building.is_copro ? 'Copropriété' : 'Simple'}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pb-4" onClick={onClick}>
        {/* Adresse avec icône */}
        <div className="flex items-start gap-2 mb-4">
          <MapPin className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
          <div className="text-sm text-muted-foreground">
            <p>{formatAddress()}</p>
            <p>{formatLocation()}</p>
          </div>
        </div>

        {/* Informations sur l'immeuble */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              Étages
            </span>
            <span className="text-sm font-medium">
              {building.floors} étage{building.floors > 1 ? 's' : ''}
            </span>
          </div>
          
          {building.is_copro && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Users className="h-3 w-3" />
                Copropriété
              </span>
              <Badge variant="outline" className="text-xs">
                Gestion collective
              </Badge>
            </div>
          )}
        </div>
      </CardContent>

      {onEdit && (
        <CardFooter className="flex gap-2 pt-4">
          <Button
            variant="default"
            size="sm"
            onClick={onClick}
            className="flex-1"
          >
            Voir
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(building.id);
            }}
            className="flex-1"
          >
            Modifier
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
