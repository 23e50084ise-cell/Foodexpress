# TODO - Deploy Render (FoodExpress)

- [ ] Agregar `gunicorn` a `requirements.txt`
- [ ] Guardar y hacer commit/push a GitHub
- [ ] En Render: redeploy del Web Service
- [ ] Verificar que el start command sea: `gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app`
- [ ] Verificar variables de entorno `FLASK_SECRET_KEY` y `MYSQL_*`
- [ ] Importar BD `foodexpress_market` usando `foodexpress/foodexpress_market.sql` (si aún no existe)
- [ ] Confirmar que Render muestre “Running” y el LINK público
