# 2022-12-07 10:38 Test VIISP script

poetry run python scripts/VIISP_xml.py

http --verify no --cert resources/request.xml https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy <  resources/prod-auth.pem

http https://test.epaslaugos.lt/portal/services/AuthenticationServiceProxy < resources/request.xml

openssl x509 -in resources/prod-auth.pem -text
openssl x509 -in resources/VIISP_test.crt -text
