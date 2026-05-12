# Metodología para la valuación de bonos de retiro tipo Merton en UDIS

## 1. Idea del instrumento

El bono de retiro se modela como un instrumento tipo SeLFIES/RSB. Su objetivo no es entregar un monto de riqueza al retiro, sino transformar el ahorro en una cantidad conocida de ingreso real futuro.

La estructura que se implementa es:

1. No hay pagos antes del retiro.
2. Al llegar a la edad de retiro, el bono comienza a pagar un cupón real anual.
3. El bono paga durante un número fijo de años.
4. No hay pago de principal al final.
5. El cupón se expresa en UDIS para mantener una unidad real de cuenta.

## 2. Adaptación a México con UDIS

La UDI permite expresar los flujos en términos reales. Por eso, si la pensión objetivo es de 72,000 UDIS anuales, el cálculo se realiza directamente en UDIS y no requiere proyectar inflación.

La curva de descuento debe ser real. En México, una aproximación natural es usar tasas reales de UDIBONOS. Como los vencimientos disponibles pueden no cubrir todos los plazos necesarios, se interpola entre los nodos disponibles y se mantiene constante la última tasa para plazos mayores.

## 3. Número de bonos

Si cada bono paga `c` UDIS anuales y el objetivo es recibir `B` UDIS anuales, entonces:

```text
N = B / c
```

Con `B = 72,000` y `c = 5`:

```text
N = 72,000 / 5 = 14,400 bonos
```

Si se define que cada bono paga 1 UDI anual, entonces el resultado sería 72,000 bonos. La app permite cambiar el cupón para dejar explícito el supuesto.

## 4. Precio del bono

Para una persona de edad `x`, con edad de retiro `R`, los años al retiro son:

```text
n = R - x
```

Si el bono paga durante `L` años, el precio en UDIS es:

```text
P_x = Σ c · (1+g)^j · v(t_j)
```

donde:

- `j = 0, 1, ..., L-1`.
- `g` es crecimiento real adicional del estándar de vida. En la versión base en UDIS, `g = 0`.
- `t_j = n + j` si el primer pago ocurre al retiro.
- `t_j = n + j + 1` si el primer pago es vencido.
- `v(t_j)` es el factor de descuento real.

Con capitalización anual:

```text
v(t) = 1 / (1 + r(t))^t
```

## 5. Costo total por edad

El costo total para comprar la pensión objetivo es:

```text
C_x = N · P_x
```

Este es el resultado más útil de la tabla, porque permite ver cuánto cuesta financiar la misma pensión si la persona empieza a comprar los bonos a los 16, 25, 35, 45 o 55 años.

## 6. Qué debe discutirse en el reporte

1. El número de bonos depende del cupón y de la pensión objetivo, no de la edad.
2. El costo sí depende de la edad, por el valor del dinero en el tiempo.
3. Usar UDIS protege contra inflación, pero no necesariamente contra riesgo de estándar de vida.
4. La versión base no usa mortalidad porque el bono no es una renta vitalicia: es un flujo por plazo fijo.
5. Si se quisiera una renta vitalicia, habría que incorporar probabilidades de supervivencia o convertir los bonos a una anualidad con una aseguradora.
