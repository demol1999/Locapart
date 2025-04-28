-- Migration SQL pour ajouter le champ user_id à la table syndicats_copro
ALTER TABLE syndicats_copro
ADD COLUMN user_id INT NULL,
ADD CONSTRAINT fk_syndicats_copro_user FOREIGN KEY (user_id) REFERENCES user_auth(id);

-- Facultatif : si tu veux remplir rétroactivement le champ user_id pour les syndicats déjà existants,
-- tu peux par exemple mettre l'ID de l'utilisateur admin ou laisser à NULL
-- UPDATE syndicats_copro SET user_id = 1 WHERE user_id IS NULL;
