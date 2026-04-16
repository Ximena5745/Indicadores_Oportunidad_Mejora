-- Ajustar tabla registros_om en Supabase para soportar la nueva lógica del proyecto

-- 1. Agregar columna tipo_accion si no existe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'registros_om' AND column_name = 'tipo_accion'
    ) THEN
        ALTER TABLE public.registros_om ADD COLUMN tipo_accion text;
    END IF;
END
$$;

-- 2. Cambiar tipo de numero_om de integer a text
ALTER TABLE public.registros_om 
ALTER COLUMN numero_om TYPE text;

-- 3. Agregar restricción única para evitar duplicados (id_indicador, periodo, anio, sede)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'registros_om_id_indicador_periodo_anio_sede_key' 
        AND conrelid = 'public.registros_om'::regclass
    ) THEN
        ALTER TABLE public.registros_om DROP CONSTRAINT registros_om_id_indicador_periodo_anio_sede_key;
    END IF;
END
$$;

ALTER TABLE public.registros_om 
ADD CONSTRAINT registros_om_unique_key UNIQUE (id_indicador, periodo, anio, sede);

-- 4. Permitir nulos
ALTER TABLE public.registros_om 
ALTER COLUMN anio DROP NOT NULL;

ALTER TABLE public.registros_om 
ALTER COLUMN proceso DROP NOT NULL;

ALTER TABLE public.registros_om 
ALTER COLUMN numero_om DROP NOT NULL;

-- 5. Valores por defecto
UPDATE public.registros_om SET tipo_accion = 'OM Kawak' WHERE tipo_accion IS NULL AND numero_om IS NOT NULL;

ALTER TABLE public.registros_om 
ALTER COLUMN tipo_accion SET DEFAULT 'OM Kawak';

-- 6. Comentarios
COMMENT ON COLUMN public.registros_om.tipo_accion IS 'Tipo de acción: OM Kawak, Reto Plan Anual, Proyecto Institucional, Otro';
COMMENT ON COLUMN public.registros_om.numero_om IS 'Número/ID de la acción (ej: número de OM, nombre del reto, etc.)';
COMMENT ON COLUMN public.registros_om.periodo IS 'Mes del incumplimiento (Enero, Febrero, etc.)';