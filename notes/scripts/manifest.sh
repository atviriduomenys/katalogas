cd ~/dev/data/katalogas

git -C ../manifest status
git -C ../manifest co master
git -C ../manifest pull

docker-compose down
docker-compose up -d
docker-compose ps
docker-compose stop mysql

docker-compose run -T --rm -e PGPASSWORD=secret postgres \
    psql -h postgres -U adp adp-dev <<EOF
BEGIN TRANSACTION;
  DROP SCHEMA "public" CASCADE;
  CREATE SCHEMA "public";
COMMIT;
EOF

http -b DELETE ":9200/haystack"

pg_restore -Fc -h localhost -U adp -d adp-dev < var/postgres_adp-dev-am.dump

poetry install

poetry run python manage.py migrate
poetry run python manage.py rebuild_index --noinput --using default

poetry run python scripts/manifest_export.py --help
poetry run python scripts/manifest_export.py --manifest-path ../manifest
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog a60d400625fbb0dcc6ba33a45ff15efa44b25c351bf4fba82d8d0233e9ef0f2a, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: unknown/sodra, catalog 8feed5c3c9dac8bf2f7f88daf57773248d7ad07e3921e981caf1605d7cba7e04, github 966d77481d36bd41c428c3552d67778e81937904e98b75fe95780bc3b816cafc
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog 90df800e7edc874a48fd84f7256e1da8b7030698c99c193813a8cafc99663999, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/sveikata, catalog afead7ff5e290de5e10a3b323a74ba605d870495cb67822162ad65438eb359fe, github 91021b124847a9a323286e92f9a2806130bd76291df2a34ecd35026bf2aaafa8
#| Hash mismatch for dataset: lsd/sveikata, catalog afead7ff5e290de5e10a3b323a74ba605d870495cb67822162ad65438eb359fe, github 91021b124847a9a323286e92f9a2806130bd76291df2a34ecd35026bf2aaafa8
#| Hash mismatch for dataset: lsd/covid19, catalog d7daa1f78cba5fb51e3324d2a55a7fb9969a2b9f3da90867573c71e1ab8c085f, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog 676046fc1b6eb09a7915cc278d6ca38a91deb3f648912897e5e26f68861cad3b, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog 9dd2a727f3cabd011b61789ae2f92fac976bfaa4eaea8eed434ea30f6c0f70d8, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog ea037ddd5a84288da97b595ebb7f837acdc9e2257a9c1b4e658c9a531ab079ee, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog 0919be43fe0748dfd2d82f6cc30f226a8e717cb959728fb8e78b2e7501387af2, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lst/standards, catalog b0f940c0bb48578956392607b13d10c4a2535cf3f1291c272d48a35573d026b5, github 9368ad99fa25b8eed3fbef3137cc07eaea28c848f1f764093e96df9eb6568e22
#| Hash mismatch for dataset: lhmt/klimatologija, catalog 8fad888edbb64e8c46b407b41cde7affcfe0f8dc2e51ea3d36f5acee898b21d1, github 2325d4b971023804730eb53ca0fbb87b33cfefdf69d6f542efbe8d7dc28fe53b
#| Hash mismatch for dataset: muitine/prekiu_kodai, catalog ce5415a44c6255243219aea3532e2d63fa6813df8ab7ea612a989304afbafb1d, github 8be75fb199caacc23d2cd0f3df8c2a9e9dca25e0129c8c1677e91e8b1075c123
#| Hash mismatch for dataset: LB/isores_sektoriaus_statistika, catalog a63414c43d049b9679164ff49cb5e60f7280fb01471cf1bfaad8f858a42abfc7, github 5a7abcafd80ec6fe81b929e7e5d81037d5e568f53d0333d908f999003cf8cc26
#| Hash mismatch for dataset: avnt/imoniu_bankrotas, catalog 166bebe4b9d9f30c6308349e6a0a9025b27be1f76c973dd80aaa36409522a51d, github 8cf4a0be8259ee244ae0140cc0eba0696d43789c622b3d483dea058dab5f97a3
#| Hash mismatch for dataset: kvjud/lu, catalog 228b7f1e6648a664a5f97c807243fca291aa75594450dc205390cb9d7539d40e, github 9d71d6238279a85384c9663f1bb7a6cb69933e449942a4a02ecf6c86a9b37c6c
#| Hash mismatch for dataset: lgt/apibendrinti_pzv_gavybos_duomenys, catalog b009fda52cb490438dbe4a2e7e6529bb52552f1dc4447703610589ee4693fdff, github 2152e4b9d2f1c8a3751b848b99c2f3553c9b2002fcc24abe07151ac2ae5181d0
#| Hash mismatch for dataset: aaa/ezeru_monitoringas, catalog 43af364a988ca08f40e821fda810e7f8331d88962c33dca3bf88ee90db192db2, github 13d4f6e1f6a6f8b47a83addf3084feaf0fd1b477062cd228e514ebebd3413d73
#| Hash mismatch for dataset: lsd/covid19, catalog cb9577832c8758fa40752ecebf93364f97d52ae44b7fee546484217ffd403d77, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: vmi/verslo_liudijimai, catalog dfab5cb2ec8bee89810f399d4ba8740fb71a19e453d3f9b2cb6da47956666d2f, github 1e646626eca22a42b2c4182fb281701b76efbc9388904f64cd358ff4245a3e45
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog 90df800e7edc874a48fd84f7256e1da8b7030698c99c193813a8cafc99663999, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: lsd/covid19, catalog 4bb6ce995e4637c16b2cac1dd5a83c6298fcb15b9caf274ede6b64ed4b3ecd3a, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: lsd/covid19, catalog a0ae9e72f50388b0028655b1f7689ce4a9a47c300b179580df35f70156906975, github f1465f9e604016bf8456a25963ed487da6cbb04676e8f10884be88a9bc89647d
#| Hash mismatch for dataset: avnt/imoniu_bankrotas, catalog 166bebe4b9d9f30c6308349e6a0a9025b27be1f76c973dd80aaa36409522a51d, github 8cf4a0be8259ee244ae0140cc0eba0696d43789c622b3d483dea058dab5f97a3
#| Hash mismatch for dataset: vsdfv/ds, catalog 359122944064aab46284fa6c0e2631fe99ae4317c87280fe2669416681c7bc6e, github e5c628c730e42edd55df91d8aa9273abbad4d4e8de308868cf5ab24026a56a25
#| Dumping 31 organization entries to orgs.csv
#| Dumping 172 dataset entries to datasets.csv
#| There are multiple dataset entries: {}
#| Error reading data from file: ../manifestdatasets/gov/lsd/svietimo_istaigos.csv
#| Error reading data from file: ../manifestdatasets/gov/lsd/miskai.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/gaminiu_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/chemijos_naudotojai.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/oro_tersalu_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/cheminiai_misiniai.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/fdujos.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/juros_mariu_bukle.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/upiu_monitoringo_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/ezeru_monitoringas.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/chemines_medziagos.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/organiniu_tirpikliu_irenginiai.csv
#| Error reading data from file: ../manifestdatasets/gov/aaa/juros_mariu_monitoringas.csv
#| Error reading data from file: ../manifestdatasets/gov/vlk/paslaugos.csv
#| Error reading data from file: ../manifestdatasets/gov/vlk/drg.csv
#| Error reading data from file: ../manifestdatasets/gov/vlk/vlk_istg.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/mokejimu_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/draudimo_bendroviu_balanso_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/pinigu_finansu_istaigu_balanso_ir_pinigu_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/isores_sektoriaus_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/investiciniu_fondu_balanso_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/pensiju_fondu_balanso_statistika.csv
#| Error reading data from file: ../manifestdatasets/gov/LB/pinigu_finansu_istaigu_paskolu_ir_indeliu_palukanu_normos.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/potencialus_tarsos_zidiniai.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/leidimas_naudoti_naudingasiais_iskasenas_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/leidimai_tirti_zemes_gelmes_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/apibendrinta_naudinguju_iskasenu_gavyba.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/geologiniu_tyrimu_ataskaitu_katalogas.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/geotopu_sarasas.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/valstybinio_pozeminio_vlm_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/vlm_vidutiniu_menesiniu_lygiu_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/geologiniai_reiskiniai_ir_procesai.csv
#| Error reading data from file: ../manifestdatasets/gov/lgt/valstybinio_pvm_hidrochemijos_duomenys.csv
#| Error reading data from file: ../manifestdatasets/gov/regitra/tp.csv
#| Error reading data from file: ../manifestdatasets/gov/muitine/prekiu_kodai.csv
#| Error reading data from file: ../manifestdatasets/gov/vmi/veiklos.csv
#| Error reading data from file: ../manifestdatasets/gov/vmi/verslo_liudijimai.csv
#| Error reading data from file: ../manifestdatasets/gov/vmi/mm_registras.csv
#| Error reading data from file: ../manifestdatasets/gov/vilnius/adresai.csv
#| Error reading data from file: ../manifestdatasets/gov/avnt/tyciniai_bankrotai.csv
#| 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 141/141 [00:00<00:00, 1256.37it/s]
#| 
#| Total CSV files found in catalog: 1127, excel files: 191, other formats: 163.
#| Standartized: 1123, random: 916.
#| Found: 187 codes in structure files.
#| Dataset mappings created: 172
#| Total files in repository: 141
#| New dataset mappings found in repository: 0
#| Organization mappings created: 31

ls ../
ls -d ../manifest*
rm -r ../manifestdatasets  ../manifestdatasets.csv  ../manifestorgs.csv

poetry run python scripts/manifest_export.py --manifest-path ../manifest
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog a60d400625fbb0dcc6ba33a45ff15efa44b25c351bf4fba82d8d0233e9ef0f2a, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: lsd/sveikata, catalog 1724cd47a621485f390fe79faab7deb1d611629e02e16cc0009c0bd1e631446f, github 100fa8ec25895926d4b3a347e7995eaef4c1c1a4f6e1b67b9e52e9536c1e6c71
#| Hash mismatch for dataset: unknown/sodra, catalog 8feed5c3c9dac8bf2f7f88daf57773248d7ad07e3921e981caf1605d7cba7e04, github 966d77481d36bd41c428c3552d67778e81937904e98b75fe95780bc3b816cafc
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog 90df800e7edc874a48fd84f7256e1da8b7030698c99c193813a8cafc99663999, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 6929f0933fa294908afad0f6730def3f4858097b5158fe09db439ec00b2f9064, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: regitra/tp, catalog ac955c859904bc878ad12138b46900526750ac4676b2186f073425fb577b7214, github 03e7fbef8db1f5f95dc1480b920b1e48b2db08e6f2a0976df8c7076e3483a4c2
#| Hash mismatch for dataset: lsd/sveikata, catalog afead7ff5e290de5e10a3b323a74ba605d870495cb67822162ad65438eb359fe, github 100fa8ec25895926d4b3a347e7995eaef4c1c1a4f6e1b67b9e52e9536c1e6c71
#| Hash mismatch for dataset: lsd/sveikata, catalog afead7ff5e290de5e10a3b323a74ba605d870495cb67822162ad65438eb359fe, github 100fa8ec25895926d4b3a347e7995eaef4c1c1a4f6e1b67b9e52e9536c1e6c71
#| Hash mismatch for dataset: lst/standards, catalog b975072fd2d54c4ca650778d8faec1d84dbc1167e5e471948c7b61cf11378331, github 2f09561d98df56a1d173c8c0957d8bbe18c5d1e0e8ba663fd9320a4198ea1031
#| Hash mismatch for dataset: lsd/covid19, catalog d7daa1f78cba5fb51e3324d2a55a7fb9969a2b9f3da90867573c71e1ab8c085f, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 676046fc1b6eb09a7915cc278d6ca38a91deb3f648912897e5e26f68861cad3b, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 9dd2a727f3cabd011b61789ae2f92fac976bfaa4eaea8eed434ea30f6c0f70d8, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog ea037ddd5a84288da97b595ebb7f837acdc9e2257a9c1b4e658c9a531ab079ee, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog 0919be43fe0748dfd2d82f6cc30f226a8e717cb959728fb8e78b2e7501387af2, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: vlk/drg, catalog 9c3eceaf0a34fcc90d1a98741359162799e62e4d173d933c2e8c4e1696757fed, github 69e8b09a74caaa2bb6e1eae020c7f33b934ea8f64c3f906b8181554a56fc0c4c
#| Hash mismatch for dataset: vlk/vlk_istg, catalog bb8aceefdf95d447791fbbc6a6e672bef6ec76e22de3dd1ac8f46857e656bb6c, github f4575bfd6edc62d0ce4790ade5f2644f18348402a86d117a0db2639eb82c5215
#| Hash mismatch for dataset: lsd/namu_ukio_biudzetas, catalog 0ee0307c1cf6b06a041602c3aea56619aa759d5deddaf99a2b7d57e5f22d7714, github 31eb0d2d14dd71b205f15a3c3ba8cb43ec8a5dea6ec2a6052ea51ac48bef7f16
#| Hash mismatch for dataset: lst/standards, catalog b0f940c0bb48578956392607b13d10c4a2535cf3f1291c272d48a35573d026b5, github 2f09561d98df56a1d173c8c0957d8bbe18c5d1e0e8ba663fd9320a4198ea1031
#| Hash mismatch for dataset: muitine/prekiu_kodai, catalog fc55aaa28541a9993906f6539150658e389624fb1b79d0d4452fd49c95fc6f5b, github ce5415a44c6255243219aea3532e2d63fa6813df8ab7ea612a989304afbafb1d
#| Hash mismatch for dataset: vsdfv/ds, catalog 07e2756e617afebd72a56eaca62cd7df57095ad55558066795e2f614c0c423b3, github 69176c678b90dd563b7ef1aa473607ac957eba521e26db2eea7e59a46d15292b
#| Hash mismatch for dataset: vmi/gyventoju_islaidos, catalog c03d5e4e70edc7967c2ec8bd340864da58c334ff184379bc00cd09b2ca7ab71b, github f1fe0e4ebd875b6029fe26601cb15485652fbafc43359545e87280df134623b7
#| Hash mismatch for dataset: vmi/gyventoju_pajamos, catalog 009b89428f543d24e474e5ca55b671b810ed5a5228ef3669491317254537d040, github 7a48269552e79e7307cb2a49b8e20e6ebb1f0008960ca0fc061ecf69e8b145cd
#| Hash mismatch for dataset: lzukt/ikmis/iverciai, catalog 538a4c926236f7a3547b1e9d37f4653be466c39c12db27860e61fa8f028dae4c, github edd2b284ffa07c8287e1e8b98cba35a67a9fd6f7e8c233a4cfb909b1145b5384
#| Hash mismatch for dataset: lzukt/ikmis/ligos, catalog 7b9de50aa088f0f5fcf8b48ce32c0aaf8527de1d9dfa881a1bb5463f907d0511, github ead49707a4ac1cdb4a20766db05224c5e3952ba392a8951e8ec12b4320969078
#| Hash mismatch for dataset: lzukt/ikmis/kenkejai, catalog d043f94e2cd1a65cccc7d65539e9991f7a3cddc674c40bfa273de664f2dac09e, github 7d9e826307bbfa7a840524a9d88228dce4e837629f0a0afbc5bbb3385a6346cb
#| Hash mismatch for dataset: vlk/paslaugos, catalog 9017faf766e8ce95ddd490a2979b63654d86b5ee18aae5d648311d746d63bda9, github 1e227a829cefff3f9b73268d77ac89d480f0eab173dd5bfe4066e1d9bd9b10b7
#| Hash mismatch for dataset: lhmt/klimatologija, catalog 52e99b0767978c0ac2d8b81a7ac54a66da83e868224265628057be13350e7b76, github 8db7700a76f16e43ca0bef4da18e087254a7ed9515dbb92275e60dc0586ea281
#| Hash mismatch for dataset: mita/horizon, catalog 55c6d7ccfe1da7d88bbe151536d978bc93e267c9a6cf618b7e9d109f50728e01, github 6fc19ade98afb5ae94950df97a662c5e981224a188632be018c2c189dc98598f
#| Hash mismatch for dataset: lhmt/klimatologija, catalog 8fad888edbb64e8c46b407b41cde7affcfe0f8dc2e51ea3d36f5acee898b21d1, github 8db7700a76f16e43ca0bef4da18e087254a7ed9515dbb92275e60dc0586ea281
#| Hash mismatch for dataset: lsd/ukio_subjektai, catalog 433739c96668256c0a399719a75a732ed16c85991e2295c510cb6c8e0dd740bb, github f755882902765828f1a6718c05cc8b68ddc7a6f7d674cbdd14eb59edb2421e15
#| Hash mismatch for dataset: avnt/tyciniai_bankrotai, catalog f2ad37351f3c5a57edf79194d9da8b50b4254e4daac215db51358dec88ac9e05, github 5379b8234eab53a783cfe2a4f941d08ce2afcfe3592c506045c7e0315f40a5f0
#| Hash mismatch for dataset: kaunas/oras, catalog a8bd3bcb284c914de9d3335e8194b9ade9a3cc277eb9a507291307871e497eee, github 6db2e69b3db4773c32d7c836cd4997dfdc1207de8d2a281f6aeb28c2cfdcfb53
#| Hash mismatch for dataset: lsd/darbo_uzmokestis, catalog 06d05422e1711ee0ae3a21897223f94e43ef06f0c53daef483a2b099204ba73b, github fbdc1f17a5b8ea70d67608048823850b44f2c601d6855cfd3a7454e070b275bd
#| Hash mismatch for dataset: muitine/muitines_istaigos, catalog 95841c0a71f9abe35b1bad1a9cb341ab96c024246374748fea141646638135ee, github 471b455eb7de9f9a8f4a8b7067221ebc9d7a23622ddc05a4d15a239e7b16da8b
#| Hash mismatch for dataset: LB/isores_sektoriaus_statistika, catalog a63414c43d049b9679164ff49cb5e60f7280fb01471cf1bfaad8f858a42abfc7, github 5a7abcafd80ec6fe81b929e7e5d81037d5e568f53d0333d908f999003cf8cc26
#| Hash mismatch for dataset: giscentras/nomenklatura, catalog 108c434eaf53e508aeb171f6e7a606645d1b24f9899bddad9f95a6d1675c2b14, github 8fdf427d5a0c9ef854b6d137a7ad3f4f0763fa1a00070bf14fb71d26d82a1028
#| Hash mismatch for dataset: vmi/pvm_deklaracijos, catalog d47946ee6a38ef7f4fbe39241e5ee41b48a28a7e994103b4a6bbe6984cd5c30c, github dfafd61ebdb136cd19ea0fb690f7ac363e2be86dac98ce41c9ca0cbd8e434137
#| Hash mismatch for dataset: vaspvt/licencijos, catalog 8d9c30c6bb1ffee51fb815cab2efabc329c051955583678fffed0b4eb6c25c34, github 6e937a60c099161f6c4fae5f22b6711a1d1025ac6ab9c9402d9e52451b387348
#| Hash mismatch for dataset: avnt/imoniu_bankrotas, catalog 166bebe4b9d9f30c6308349e6a0a9025b27be1f76c973dd80aaa36409522a51d, github ce0f9896570ef2ea8c25dbf284ff215fc4544b9c0a795f3bc673dbeca8205305
#| Hash mismatch for dataset: avnt/imoniu_bankrotas, catalog 166bebe4b9d9f30c6308349e6a0a9025b27be1f76c973dd80aaa36409522a51d, github ce0f9896570ef2ea8c25dbf284ff215fc4544b9c0a795f3bc673dbeca8205305
#| Hash mismatch for dataset: vmi/nt, catalog bfc55c92366902f2a8408bab7e292673f81f322a7fe02ac537d66593472e4191, github fbb2f50d683b86cb8e8c1dc6d33021ff05b27b8c62227a34a26fc1770dec4780
#| Hash mismatch for dataset: vlk/tlk10am, catalog 2170192474ec2093a0f686e2e90c752a484fac13ba69074f518de4a94ffc4a5a, github 0c775753f60aebcffa4d7a7a83b963158430b27b1885bf4cefe410bac515e268
#| Hash mismatch for dataset: vmi/verslo_liudijimai, catalog 9b0af7c4bc5b7f8a3714101c9223a10c9afd9587d4a3c15cdae292bf6046aabf, github edffacc6fb1e2f24b49b684e60f787402c92067ac1472c078334e3ed68d76ce6
#| Hash mismatch for dataset: bpc/pagalbos_skambuciai, catalog 72f534a741b6cc0240ad33be368cedf3b09e1ca7d63f5bb6b72a63d7371fa508, github 95799a63401b5b55424712a4717800e24bbad4e97c82098ac87c8c5524a84ea7
#| Hash mismatch for dataset: vmi/zemes_mokestis, catalog de24bccdc1e504784415a57a82b41bf54eab5e88a79777cc39ac2f101188f75d, github 20dd8ddc5bcf29a4a599f3ced29b6c20dac6b407bf7a87199eb70198f47e22e7
#| Hash mismatch for dataset: lsd/gyventoju_uzimtumas, catalog 3f89816ee6d72e4134227b4865b690d08d2e92b1e7bfdbea23fbf3fe634e1d94, github 043819803382061c2ae8dcd1a0e7b5f02e07b0ba2d9fd37c6ee93b886f085380
#| Hash mismatch for dataset: lsd/it_naudojimas_namu_ukiuose, catalog f5ca5ce3d78249cbb566516271912881155985637589d092a762049ac82ce2a1, github 9c657ec76979ed5dab4615649b3cdff4964bba5afa0031d3e79a0bcb47052eb5
#| Hash mismatch for dataset: aaa/juros_mariu_monitoringas, catalog 74cddfe964fd36a99f4767e5de6a788b1185a29ffa169beca2214140193b2dd3, github 817b718c48efe2e69a9f38a10569d2cdca270a5bac54d536b27219555b711879
#| Hash mismatch for dataset: aaa/juros_mariu_bukle, catalog 0a471241ea5ae59794b3cc0acb5ce869f09c419b139e72cfc3b0a199eaf536f8, github aa2c8a6b1938cad32078e4e120e01dd4cd2e3948b084e74f31bd9ab7685dd751
#| Hash mismatch for dataset: lsd/pajamu_ir_gyvenimo_salygos, catalog 0675d0b9e3634b7d435e5e74c2cb74efd5761f7e797421353e7393b219ca90a7, github 9fecde01ef782c192e7feb8c706bfd42c2377922d91a1992042f0783f5d0d730
#| Hash mismatch for dataset: urm/vbpdp, catalog 2b32fd8a84a5edcd1830cbb8156c6dca23befd282eba26e6f10fc52d664de114, github d51f2d8c4d505a42598bcc374b386f7612922f8a64b0cf6abdebd326078239d7
#| Hash mismatch for dataset: urm/vr, catalog 4fcf1971b8a1ae8f9a94f19d65b43b64e5b61091ae4a4c8793b19da7253db4ad, github 684c9fcc070fa27664916c574f604fd25d813ad125188da01746840226d1ff79
#| Hash mismatch for dataset: urm/vmdu, catalog 6b7f5f83581db539db14e171fce04cc73af114b6e85562f42a80abace8a6f864, github ff6a42f83a9bec6746c3d1c567a4b0d0d25c6772cebb3c7e9c1a13a8e6226609
#| Hash mismatch for dataset: vsdfv/pensijos, catalog 8c547b424fbec60a6d1ce41b5fffd160d79b3c5c395b484da9dbb747a6f0ed2c, github 0f5e3adfdf34dbf05b165b40f1b313ee260045b1ea0f131035386faf28dcba48
#| Hash mismatch for dataset: vsdfv/nedarbo_ismokos, catalog b4ae88388abe4fb94dc6ce5e6c810d57b4b9093ad0ac03ddd9871352a99c3c6c, github 9115b3d02a46115009dd7627bb3d05585a0383a6c474bc3440b817cb42010e5c
#| Hash mismatch for dataset: vsdfv/nelaimingi_atsitikimai, catalog 1462d84afd113d0e7dfc73d93ecb767d5222c61ab84830766c2d0a21c827ed31, github 19e81479bae700b843b307d18035c3a3a80aeaada808a56568a04dc29a384bea
#| Hash mismatch for dataset: vsdfv/pasalpos, catalog b3db36db5bd99e82726ade7f27e2b6c2ea65ec58322ecec4c980d60f424df37c, github 5c87bf2348de3763b336b991e08544c15f89c0203c6b4195ca783d23d1e99d24
#| Hash mismatch for dataset: vsdfv/sdi, catalog ddc938ff2027ac838f262b2d351500d94f3b4201f5c359799918c58783ed876b, github a1218508d0546ea04e2cffef440ab36e0d2e7c43f36d3186741d1da2dc6b8c10
#| Hash mismatch for dataset: vsdfv/apdraustieji, catalog 8ff38b17f8c5d02eb15b22a3fd33d5f52dfbc0e08a2228b6ecf7577063e92909, github a5ae7a8ceb4bc0da5258c1ac6c2caea1441afdfeb36b77e5cdfa8c84afba4afe
#| Hash mismatch for dataset: vsdfv/pkdalyviai, catalog 57057af247eb876084b6a4897922e11a1602a65adcf8360f12cd14c738ce1aac, github 39a20cff8ea6ccb9f9a772b5bffc4b16f7facf7e02c53933168afd53d53f1199
#| Hash mismatch for dataset: vsdfv/pkismokos, catalog c4238bdb84f78684e050cef084277aa70fb4f6d37c352c32865b7c565b0d9488, github 26cb651406983d649b879f42cfabd1bc5badd9fff44ca0376a4e32dc2bee32eb
#| Hash mismatch for dataset: vsdfv/pkbendroves, catalog bcb88e80bae74b4d0444ef13f5060b811d851dac66d7b3d0a7a1e25270552ba7, github 45c4cae26affe3e8cba59b41317855edc74f6de76450f3d55b66b86821e6713d
#| Hash mismatch for dataset: lakd/aplinkosauga, catalog cd5f041c517d0cce3877e7a1659b58be18344087d1cc3a79e8c4cefaf34ed5b1, github ffa2c9ce095ee8bf9096e2d7e584079898dd4ae4e2c69c963cb78be383c881dc
#| Hash mismatch for dataset: kvjud/lu, catalog 228b7f1e6648a664a5f97c807243fca291aa75594450dc205390cb9d7539d40e, github 9d71d6238279a85384c9663f1bb7a6cb69933e449942a4a02ecf6c86a9b37c6c
#| Hash mismatch for dataset: lgt/apibendrinti_pzv_gavybos_duomenys, catalog b009fda52cb490438dbe4a2e7e6529bb52552f1dc4447703610589ee4693fdff, github 2152e4b9d2f1c8a3751b848b99c2f3553c9b2002fcc24abe07151ac2ae5181d0
#| Hash mismatch for dataset: lsd/grid, catalog 7c5342f368285fc54c7fcc5bc494c5d347e79e0a90baa2f858242bca22469331, github 46b5eb0f43f69455db387c3de383439110b34632cc1b27c98c13a2b46269789b
#| Hash mismatch for dataset: aaa/ezeru_monitoringas, catalog 5bc6ca2f3197554e91bdbf686e148a6c93f33b90deecc0b71067d9bc66c824c7, github 4afee4cc3981bc654c2f8b67219dd891fe01954741b59c1e3b058fcc23149952
#| Hash mismatch for dataset: aaa/organiniu_tirpikliu_irenginiai, catalog 0126e6c55490b524f4d3a6b3221295a421738229fb9451246ea98ceda5f61ed9, github 1b4949aea75f72884f94bce08c1dbb9d274f799dde9c0fbdfb27658e7bb88bdb
#| Hash mismatch for dataset: aaa/oro_tersalu_duomenys, catalog e7fb686926274e3dabf50552e2e2d034a46a294b533dd1deac5003e57c486b68, github bb24ccbe9ff51d1d5d43c617af4a93ad1bd25512df66a2786d2dd902c862b8d1
#| Hash mismatch for dataset: vk/bva, catalog 28fb3121b24a4fd3b4a245bb079252c1108f6e7b97faa16e883714923fdf6565, github 350b7d3644f3172392635688ddbb5d4d6a5f09097e6cc545100e7198bc33ecdc
#| Hash mismatch for dataset: vk/fba, catalog 8a0307eaa371caeca3e710556492dd215a657af3ee9aceff408b5ede153b1741, github a28940438521bd2be6a1bb94cab26a2de32ceb6f22240a830e2a94ee89b28b13
#| Hash mismatch for dataset: vk/apdovanojimai, catalog b548761ab71d4b6b3dd34a568e1366e94ce64c9959bd40efaf5e98127d2bbab3, github 5f1c72f7f7d1670e82a3ee2d8987da39bf1a8205a22acacb5515eaa706cfd445
#| Hash mismatch for dataset: vk/vra, catalog d9fcdc38523919c6d790bad853ea4da209b50ad12689f51d58f7d6154dacaf3d, github 5466b9fc29654c6608fcd29226cf6994ab1c6267c5c3d0c08e4bc84c0fedf64f
#| Hash mismatch for dataset: vk/alga, catalog 4544cd8a13ee10be254c5bd43be9ffd82a0f507cba734c6a3e2556187c40100b, github 97d572ed6dec7e428ebb1a2b659de3732d6469fade20a7aebcc40d2ebf7e4171
#| Hash mismatch for dataset: lgt/potencialus_tarsos_zidiniai, catalog da5ab96214d1f65ac016c3f7704fd075524cde13cda56e37831ed7eeb6d94e29, github e704c6893a0585f6a147c73ea4e75eb2782e73d5f25e61a78b5b2454e223863a
#| Hash mismatch for dataset: lsd/svietimo_istaigos, catalog 5b467ab247ad31d4549e004df7a4b6be145f5c3601d6deba1f1b55d645e5ff1c, github e7221bef4dc8f3565aaa9b3d1056b0f69ebcd46896e441592954398aea07c69c
#| Hash mismatch for dataset: aaa/ezeru_monitoringas, catalog 43af364a988ca08f40e821fda810e7f8331d88962c33dca3bf88ee90db192db2, github 4afee4cc3981bc654c2f8b67219dd891fe01954741b59c1e3b058fcc23149952
#| Hash mismatch for dataset: aaa/upiu_monitoringo_duomenys, catalog a8ae6b7a71125fb2d8f4d0ebf29902109cf42e809093ddabe575a63fded069e9, github 54a975085af87952dfa3226afa2644deafd73d44101b0446ef19eaca1c8a80da
#| Hash mismatch for dataset: aaa/gaminiu_duomenys, catalog 056e51b5d93f05d84b10df89582d470bdfb7d2112fe4b2d005d774fd300424bf, github 7510f0c5b73fa6079a451d9d5334bbc3f9a263a14566e3881cfcebf4ce7f773f
#| Hash mismatch for dataset: vmi/mm_registras, catalog 8d751063a7e3d816223ecc814653f206dc4966b267096ebf0aa058888a5dc9ec, github d624969920996662488d8ee107843c136250f126879929efcf2312f84b0c1eaf
#| Hash mismatch for dataset: lsd/covid19, catalog cb9577832c8758fa40752ecebf93364f97d52ae44b7fee546484217ffd403d77, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: vmi/verslo_liudijimai, catalog dfab5cb2ec8bee89810f399d4ba8740fb71a19e453d3f9b2cb6da47956666d2f, github edffacc6fb1e2f24b49b684e60f787402c92067ac1472c078334e3ed68d76ce6
#| Hash mismatch for dataset: aaa/chemijos_naudotojai, catalog 69f1cccf3e107288690fd36580b5b10d4baa4aa002cf6858b7bf0919abbe5305, github a1b7e579c4948cde06ca1acce1130a6af6d935b942b5b0b8d983aee6153314a8
#| Hash mismatch for dataset: aaa/cheminiai_misiniai, catalog 2366ddf44f5433bf94db163e3565339c6c3820a771501d24900c5a00121f135f, github 4c0ce878be772b9cd41cd8b8609818828d4be0b2e074d2af72b193df3402b77b
#| Hash mismatch for dataset: aaa/chemines_medziagos, catalog 7d6b30064d98d7316073d126eda711fa65614ccc0ccd041b93ed4d3e1f46cab1, github 6df935e8d470d782dfa9a94e93ceeeb9419920d57be8575fe3482008549caa28
#| Hash mismatch for dataset: lsd/svietimas/suaugusiuju, catalog 90df800e7edc874a48fd84f7256e1da8b7030698c99c193813a8cafc99663999, github 5a9731b8d3329a2da6a96395796136efa58adfcb4b6399f58765369ec236516c
#| Hash mismatch for dataset: lsd/covid19, catalog 4bb6ce995e4637c16b2cac1dd5a83c6298fcb15b9caf274ede6b64ed4b3ecd3a, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: lsd/covid19, catalog a0ae9e72f50388b0028655b1f7689ce4a9a47c300b179580df35f70156906975, github f571b9184116ee40ac3068d43fdfd4e7413342c6ccceff00f4ad80d42b6850ae
#| Hash mismatch for dataset: avnt/imoniu_bankrotas, catalog 166bebe4b9d9f30c6308349e6a0a9025b27be1f76c973dd80aaa36409522a51d, github ce0f9896570ef2ea8c25dbf284ff215fc4544b9c0a795f3bc673dbeca8205305
#| Hash mismatch for dataset: avnt/imoniu_restrukturizavimas, catalog 95f5977223ea177d3851d69c3a7681d658787ec16561ff97ad3896f3d8f80616, github 315f7181de9d8d0db54c815622c9b235938c874b40ae0beb596397527377fa80
#| Hash mismatch for dataset: giscentras/grpk, catalog 45fba006ba755bbcfa0332b7516c47a31242fb64888d183914df33ca05743b3b, github eb4cf9b5033786f20c8de1c996b1944417250338dff06a1a6f9497db42bee281
#| Hash mismatch for dataset: vsdfv/ds, catalog 359122944064aab46284fa6c0e2631fe99ae4317c87280fe2669416681c7bc6e, github 69176c678b90dd563b7ef1aa473607ac957eba521e26db2eea7e59a46d15292b
#| Hash mismatch for dataset: vsdfv/vap, catalog 00a47399c742e1d934af9d30366634c86f8d7a92e9e514fee7b20d835698fe28, github b7ee00fa05dcb240fc11b2ae6fb801da23d3fc1edaa682d725e94e16adb8ec3e
#| Hash mismatch for dataset: aaa/fdujos, catalog 9b18881dbebb26580c40c20923c070965f4f585359e72354176b1c3d8f4645d5, github e8ad031dc8c209c0b3fdbda17806fb373d0c0456b267636cbe963071e6bc20ee
#| Dumping 31 organization entries to orgs.csv
#| Dumping 172 dataset entries to datasets.csv
#| Error reading data from file: ../manifest/datasets/gov/lsd/miskai.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/mokejimu_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/draudimo_bendroviu_balanso_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/pinigu_finansu_istaigu_balanso_ir_pinigu_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/isores_sektoriaus_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/investiciniu_fondu_balanso_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/pensiju_fondu_balanso_statistika.csv
#| Error reading data from file: ../manifest/datasets/gov/LB/pinigu_finansu_istaigu_paskolu_ir_indeliu_palukanu_normos.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/leidimas_naudoti_naudingasiais_iskasenas_duomenys.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/leidimai_tirti_zemes_gelmes_duomenys.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/apibendrinta_naudinguju_iskasenu_gavyba.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/geologiniu_tyrimu_ataskaitu_katalogas.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/geotopu_sarasas.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/valstybinio_pozeminio_vlm_duomenys.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/vlm_vidutiniu_menesiniu_lygiu_duomenys.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/geologiniai_reiskiniai_ir_procesai.csv
#| Error reading data from file: ../manifest/datasets/gov/lgt/valstybinio_pvm_hidrochemijos_duomenys.csv
#| Error reading data from file: ../manifest/datasets/gov/vmi/veiklos.csv
#| Error reading data from file: ../manifest/datasets/gov/vilnius/adresai.csv
#| Total CSV files found in catalog: 1127, excel files: 191, other formats: 163.
#| Standartized: 1123, random: 916.
#| Found: 187 codes in structure files.
#| Dataset mappings created: 172
#| Total files in repository: 621
#| New dataset mappings found in repository: 454
#| Organization mappings created: 31

ls -l ..
git -C ../manifest status
ls ../manifest/
ls -1 ../manifest/datasets/gov


docker-compose run -T --rm -e PGPASSWORD=secret postgres psql -h postgres -U adp adp-dev <<EOF
\dt
EOF
#|                           List of relations
#|  Schema |                    Name                     | Type  | Owner 
#| --------+---------------------------------------------+-------+-------
#|  public | organization                                | table | adp
docker-compose run -T --rm -e PGPASSWORD=secret postgres psql -h postgres -U adp adp-dev <<EOF
\d organization
EOF
#|                                         Table "public.organization"
#|     Column    |           Type           | Collation | Nullable |                 Default                  
#| --------------+--------------------------+-----------+----------+------------------------------------------
#|  id           | bigint                   |           | not null | nextval('organization_id_seq'::regclass)
#|  created      | timestamp with time zone |           |          | 
#|  modified     | timestamp with time zone |           |          | 
#|  version      | bigint                   |           | not null | 
#|  description  | text                     |           |          | 
#|  municipality | character varying(255)   |           |          | 
#|  region       | character varying(255)   |           |          | 
#|  slug         | character varying(255)   |           |          | 
#|  title        | text                     |           |          | 
#|  uuid         | character(36)            |           |          | 
#|  deleted      | boolean                  |           |          | 
#|  deleted_on   | timestamp with time zone |           |          | 
#|  address      | character varying(255)   |           |          | 
#|  company_code | character varying(255)   |           |          | 
#|  email        | character varying(255)   |           |          | 
#|  is_public    | boolean                  |           |          | 
#|  phone        | character varying(255)   |           |          | 
#|  jurisdiction | character varying(255)   |           |          | 
#|  website      | character varying(255)   |           |          | 
#|  imageuuid    | character(36)            |           |          | 
#|  role         | character varying(255)   |           |          | 
#|  depth        | integer                  |           | not null | 
#|  kind         | character varying(36)    |           | not null | 
#|  numchild     | integer                  |           | not null | 
#|  path         | character varying(255)   |           | not null | 
#|  image_id     | integer                  |           |          | 
#|  provider     | boolean                  |           | not null | 
#|  name         | text                     |           |          | 
docker-compose run -T --rm -e PGPASSWORD=secret postgres psql -h postgres -U adp adp-dev <<EOF
SELECT id, company_code, name, title, jurisdiction FROM organization;
EOF
#|  id  |   company_code    | name |                                                     title                                                     |                   jurisdiction                    
#| -----+-------------------+------+---------------------------------------------------------------------------------------------------------------+---------------------------------------------------
#|    2 | 288739270         |      | Nacionalinė mokėjimo agentūra prie Žemės ūkio ministerijos                                                    | Žemės ūkio ministerija
#|    1 | 305238040         |      | Nacionalinė švietimo agentūra                                                                                 | Švietimo, mokslo ir sporto ministerija
#|   11 | 188710823         |      | Klaipėdos miesto savivaldybės administracija                                                                  | Savivaldybės
#|   15 | 304151376         |      | AB „Energijos skirstymo operatorius“                                                                          | Energetikos ministerija
#|   16 | 188605295         |      | Lietuvos Respublikos Seimo kanceliarija                                                                       | Prezidentūrai ir Seimui atskaitingos institucijos
#|   62 | 188770044         |      | Valstybinė vartotojų teisių apsaugos tarnyba                                                                  | Teisingumo ministerija
#|    8 | 306205513         |      | VĮ Žemės ūkio duomenų centras                                                                                 | Žemės ūkio ministerija
#|  132 | 110078991         |      | Valstybės įmonė „REGITRA“                                                                                     | Vidaus reikalų ministerija
#|  101 | 188711925         |      | Visagino savivaldybės administracija                                                                          | Vidaus reikalų ministerija
#|   66 | 188715222         |      | Kretingos rajono savivaldybės administracija                                                                  | Vidaus reikalų ministerija
#|  113 | 188710976         |      | Nacionalinis akreditacijos biuras                                                                             | Ekonomikos ir inovacijų ministerija
#|   23 | 188710638         |      | Lietuvos automobilių kelių direkcija                                                                          | Susisiekimo ministerija
#|   35 | 302526112         |      | Valstybinė augalininkystės tarnyba prie Žemės ūkio ministerijos                                               | Žemės ūkio ministerija
#|   76 | 290757560         |      | Lietuvos nacionalinė Martyno Mažvydo biblioteka                                                               | Kultūros ministerija
#|  161 | 188710780         |      | Lietuvos geologijos tarnyba prie Aplinkos ministerijos                                                        | Aplinkos ministerija
#|   91 | 188640467         |      | Lietuvos standartizacijos departamentas                                                                       | Ekonomikos ir inovacijų ministerija
#|    4 | 188711163         |      | Lietuvos Respublikos valstybinė darbo inspekcija prie Socialinės apsaugos ir darbo ministerijos               | Socialinės apsaugos ir darbo ministerija
#|  195 | 124364561         |      | VšĮ Vilniaus universiteto ligoninė Santaros klinikos                                                          | Sveikatos apsaugos ministerija
#|   57 |                   |      | VĮ "Lietuvos naftos produktų agentūra"                                                                        | 
#|  116 |                   |      | Nacionalinis egzaminų centras                                                                                 | 
#|   13 | 122588443         |      | UAB ATEA                                                                                                      | Verslas
#|  277 |                   |      | Nevyriausybinės organizacijos                                                                                 | 
#|    6 | 288601650         |      | Lietuvos Respublikos finansų ministerija                                                                      | Finansų ministerija
#|    5 |                   |      | Žemės ūkio informacijos ir kaimo verslo centras                                                               | 
#|   80 | 304157094         |      | Audito, apskaitos, turto vertinimo ir nemokumo valdymo tarnyba prie Lietuvos Respublikos finansų ministerijos | Finansų ministerija
#|   26 | 188656838         |      | Muitinės departamentas prie Lietuvos Respublikos finansų ministerijos                                         | Finansų ministerija
#|   47 | 126125624         |      | VŠĮ Centrinė projektų valdymo agentūra                                                                        | Finansų ministerija
#|   59 | 188694162         |      | Valstybės dokumentų technologinės apsaugos tarnyba                                                            | Finansų ministerija
#|   82 | 188772052         |      | Lošimų priežiūros tarnyba prie Finansų ministerijos                                                           | Finansų ministerija
#|   83 | 188659752         |      | Valstybinė mokesčių inspekcija prie Finansų ministerijos                                                      | Finansų ministerija
#|  192 | 303039520         |      | Viešųjų investicijų plėtros agentūra                                                                          | Finansų ministerija
#|   39 | 193114935         |      | Nacionalinis transplantacijos biuras prie Sveikatos apsaugos ministerijos                                     | Sveikatos apsaugos ministerija
#|   58 | 302427477         |      | Užkrečiamųjų ligų ir AIDS centras                                                                             | Sveikatos apsaugos ministerija
#|   69 | 191351864         |      | Valstybinė vaistų kontrolės tarnyba                                                                           | Sveikatos apsaugos ministerija
#|   96 | 193288633         |      | Radiacinės saugos centras                                                                                     | Sveikatos apsaugos ministerija
#|  103 | 126413338         |      | VšĮ Nacionalinis kraujo centras                                                                               | Sveikatos apsaugos ministerija
#|  110 | 291349070         |      | Nacionalinis visuomenės sveikatos centras prie Sveikatos apsaugos ministerijos                                | Sveikatos apsaugos ministerija
#|  123 | 302610311         |      | Narkotikų, tabako ir alkoholio kontrolės departamentas                                                        | Sveikatos apsaugos ministerija
#|  136 | 190273081         |      | Viešoji įstaiga Alytaus apskrities tuberkuliozės ligoninė                                                     | Sveikatos apsaugos ministerija
#|  151 | 124368392         |      | Viešoji įstaiga "VILNIAUS GIMDYMO NAMAI"                                                                      | Sveikatos apsaugos ministerija
#|  168 | 191349831         |      | Sveikatos apsaugos ministerijos Ekstremalių sveikatai situacijų centras                                       | Sveikatos apsaugos ministerija
#|   17 | 111958286         |      | Higienos institutas                                                                                           | Sveikatos apsaugos ministerija
#|   65 | 191352247         |      | Valstybinė akreditavimo sveikatos priežiūros veiklai tarnyba prie Sveikatos apsaugos ministerijos             | Sveikatos apsaugos ministerija
#|   12 | 135163499         |      | Lietuvos sveikatos mokslų universiteto ligoninė Kauno klinikos                                                | Sveikatos apsaugos ministerija
#|  164 | 302583800         |      | Lietuvos sveikatos mokslų universiteto Kauno ligoninė                                                         | Sveikatos apsaugos ministerija
#|  152 | 191351679         |      | Valstybinė ligonių kasa prie Sveikatos apsaugos ministerijos                                                  | Sveikatos apsaugos ministerija
#|  160 | 191340120         |      | VŠĮ Respublikinė Panevėžio ligoninė                                                                           | Sveikatos apsaugos ministerija
#|   60 | 188710595         |      | Lietuvos bioetikos komitetas                                                                                  | Sveikatos apsaugos ministerija
#|  181 | 124243848         |      | VšĮ Respublikinė Vilniaus universitetinė ligoninė                                                             | Sveikatos apsaugos ministerija
#|  202 | 235042580         |      | Viešoji įstaiga Kauno miesto greitosios medicinos pagalbos stotis                                             | Sveikatos apsaugos ministerija
#|  210 | 191744287         |      | VšĮ Vilniaus universiteto ligoninės Žalgirio klinika                                                          | Sveikatos apsaugos ministerija
#|  211 | 152682464         |      | VšĮ Palangos vaikų reabilitacijos sanatorija "Palangos gintaras"                                              | Sveikatos apsaugos ministerija
#|  215 | 191671615         |      | Valstybinės teismo psichiatrijos tarnyba prie Sveikatos apsaugos ministerijos                                 | Sveikatos apsaugos ministerija
#|  217 | 245386220         |      | Viešoji įstaiga Respublikinė Šiaulių ligoninė                                                                 | Sveikatos apsaugos ministerija
#|  219 | 190999616         |      | Respublikinis priklausomybės ligų centras                                                                     | Sveikatos apsaugos ministerija
#|  224 | 191340469         |      | Viešoji įstaiga Klaipėdos jūrininkų ligoninė                                                                  | Sveikatos apsaugos ministerija
#|  227 | 191351145         |      | Lietuvos medicinos biblioteka                                                                                 | Sveikatos apsaugos ministerija
#|  228 |  191351145        |      | Lietuvos medicinos biblioteka                                                                                 | Sveikatos apsaugos ministerija
#|  231 | 302583800         |      | VšĮ Lietuvos sveikatos mokslų universiteto Kauno ligoninė                                                     | Sveikatos apsaugos ministerija
#|  232 | 191351330         |      | Valstybinė teismo medicinos tarnyba                                                                           | Sveikatos apsaugos ministerija
#|  236 | 182935350         |      | VšĮ Ukmergės ligoninė                                                                                         | Sveikatos apsaugos ministerija
#|  204 | 124247526         |      | VŠĮ Respublikinė Vilniaus psichiatrijos ligoninė                                                              | Sveikatos apsaugos ministerija
#|  207 | 173222266         |      | VšĮ Rokiškio psichiatrijos ligoninė                                                                           | Sveikatos apsaugos ministerija
#|  212 | 195551983         |      | Nacionalinė visuomenės sveikatos priežiūros laboratorija                                                      | Sveikatos apsaugos ministerija
#|  221 | 191340088         |      | VšĮ Respublikinė Klaipėdos ligoninė                                                                           | Sveikatos apsaugos ministerija
#|  237 | 190272175         |      | Viešoji įstaiga Alytaus apskrities S. Kudirkos ligoninė                                                       | Sveikatos apsaugos ministerija
#|  238 | 165803154         |      | Viešoji įstaiga Marijampolės ligoninė                                                                         | Sveikatos apsaugos ministerija
#|  239 | 179761936         |      | Viešoji įstaiga Tauragės ligoninė                                                                             | Sveikatos apsaugos ministerija
#|  272 | 166913899         |      | Viešoji įstaiga Regioninė Mažeikių ligoninė                                                                   | Sveikatos apsaugos ministerija
#|   64 | 188708943         |      | Lietuvos Respublikos valstybinis patentų biuras                                                               | Teisingumo ministerija
#|   90 | 188724424         |      | Nacionalinė teismų administracija                                                                             | Teisingumo ministerija
#|   95 | 124110246         |      | Valstybės įmonė Registrų centras                                                                              | Teisingumo ministerija
#|  140 | 111952632         |      | Lietuvos teismo ekspertizės centras                                                                           | Teisingumo ministerija
#|  171 | 288697120         |      | Kalėjimų departamentas prie Lietuvos Respublikos teisingumo ministerijos                                      | Teisingumo ministerija
#|  222 | 304834984         |      | Lietuvos probacijos tarnyba                                                                                   | Teisingumo ministerija
#|  242 | 126198978         |      | Lietuvos antstolių rūmai                                                                                      | Teisingumo ministerija
#|   20 | 188604955         |      | Lietuvos Respublikos teisingumo ministerija                                                                   | Teisingumo ministerija
#|   25 |                   |      | VĮ Registrų centras, Lietuvos antstolių rūmai                                                                 | 
#|   36 | 188613242         |      | Lietuvos Respublikos užsienio reikalų ministerija                                                             | Užsienio reikalų ministerija
#|   24 | 188772248         |      | Rokiškio rajono savivaldybės administracija                                                                   | Vidaus reikalų ministerija
#|   28 | 188642660         |      | Biržų rajono savivaldybės administracija                                                                      | Savivaldybės
#|  166 | 125817744         |      | Valstybės garantuojamos teisinės pagalbos tarnyba                                                             | Teisingumo ministerija
#|   14 | 188603472         |      | Lietuvos Respublikos  sveikatos apsaugos ministerija                                                          | Sveikatos apsaugos ministerija
#|   34 | 188774975         |      | Kupškio rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|   41 | 188785847         |      | Policijos departamentas prie Vidaus reikalų ministerijos                                                      | Vidaus reikalų ministerija
#|   67 | 188766722         |      | Švenčionių rajono savivaldybės administracija                                                                 | Vidaus reikalų ministerija
#|   77 | 188712799         |      | Molėtų rajono savivaldybės administracija                                                                     | Vidaus reikalų ministerija
#|   85 | 188608252         |      | Valstybės sienos apsaugos tarnyba                                                                             | Vidaus reikalų ministerija
#|   86 | 188784211         |      | Valstybės tarnybos departamentas                                                                              | Vidaus reikalų ministerija
#|  105 | 188787474         |      | Bendrasis pagalbos centras                                                                                    | Vidaus reikalų ministerija
#|  108 | 188608786         |      | Finansinių nusikaltimų tyrimo tarnyba                                                                         | Vidaus reikalų ministerija
#|  114 | 188601311         |      | Priešgaisrinės apsaugos ir gelbėjimo departamentas prie Vidaus reikalų ministerijos                           | Vidaus reikalų ministerija
#|  119 | 188713933         |      | Jurbarko rajono savivaldybės administracija                                                                   | Vidaus reikalų ministerija
#|  121 | 188774822         |      | Informatikos ir ryšių departamentas prie Lietuvos Respublikos vidaus reikalų ministerijos                     | Vidaus reikalų ministerija
#|  126 | 188764867         |      | Kauno miesto savivaldybės administracija                                                                      | Vidaus reikalų ministerija
#|  127 | 188737457         |      | Tauragės rajono savivaldybės administracija                                                                   | Vidaus reikalų ministerija
#|  131 | 188719391         |      | Akmenės rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|   87 | 188723322         |      | Šilutės rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|  130 | 188726051         |      | Šiaulių rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|  128 | 188776264         |      | Druskininkų savivaldybės administracija                                                                       | Vidaus reikalų ministerija
#|  133 | 125196077         |      | Palangos miesto savivaldybė                                                                                   | Vidaus reikalų ministerija
#|  135 | 188773720         |      | Šilalės rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|  137 | 188756190         |      | Elektrėnų savivaldybės administracija                                                                         | Vidaus reikalų ministerija
#|  138 | 188714992         |      | Lazdijų rajono savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|  139 |  181626536        |      | Trakų rajono savivaldybės administracija                                                                      | Vidaus reikalų ministerija
#|  145 | 188753461         |      | Zarasų rajono savivaldybės administracija                                                                     | Vidaus reikalų ministerija
#|  147 | 188771865         |      | Šiaulių miesto savivaldybės administracija                                                                    | Vidaus reikalų ministerija
#|  176 | 188710061         |      | Vilniaus miesto savivaldybės administracija                                                                   | Vidaus reikalų ministerija
#|  186 | 188610666         |      | Migracijos departamentas prie Lietuvos Respublikos vidaus reikalų ministerijos                                | Vidaus reikalų ministerija
#|   40 | 188601464         |      | Lietuvos Respublikos vidaus reikalų ministerija                                                               | Vidaus reikalų ministerija
#|   93 | 191769098         |      | Lietuvos Respublikos ginklų fondas prie Lietuvos Respublikos vidaus reikalų ministerijos                      | 
#|   70 | 188606625         |      | Valstybinė energetikos inspekcija prie Energetikos ministerijos                                               | Energetikos ministerija
#|   88 | 304937660         |      | Viešoji įstaiga Lietuvos energetikos agentūra                                                                 | Energetikos ministerija
#|  104 | 188706554         |      | Valstybinė kainų ir energetikos kontrolės komisija                                                            | Energetikos ministerija
#|  198 | 304151376         |      |                                                                                                               | Energetikos ministerija
#|  209 | 188706554         |      | Valstybinė energetikos reguliavimo taryba                                                                     | Energetikos ministerija
#|  243 | 110084364         |      | VĮ Naftos produktų agentūra                                                                                   | Energetikos ministerija
#|  159 | 188769113         |      | Marijampolės savivaldybės administracija                                                                      | Vidaus reikalų ministerija
#|   22 |         188647255 |      | Valstybinė kelių transporto inspekcija                                                                        | Susisiekimo ministerija
#|   32 | 288771670         |      | Civilinės aviacijos administracija                                                                            | Susisiekimo ministerija
#|   61 | 120864074         |      | Valstybės įmonė Lietuvos oro uostai                                                                           | Susisiekimo ministerija
#|   63 | 188647255         |      | Lietuvos saugios laivybos administracija                                                                      | Susisiekimo ministerija
#|   74 | 188683714         |      | Valstybinė geležinkelio inspekcija prie Susisiekimo ministerijos                                              | Susisiekimo ministerija
#|  102 | 240329870         |      | VĮ Klaipėdos valstybinio jūrų uosto direkcija                                                                 | Susisiekimo ministerija
#|  118 | 300147455         |      | Pasienio kontrolės punktų direkcija prie Susisiekimo ministerijos                                             | Susisiekimo ministerija
#|  185 |  232112130        |      | Akcinė bendrovė „Kelių priežiūra"                                                                             | Susisiekimo ministerija
#|  188 | 188647255         |      | Lietuvos transporto saugos administracija                                                                     | Susisiekimo ministerija
#|  206 | 132090925         |      | AB Vidaus vandens kelių direkcija                                                                             | Susisiekimo ministerija
#|  214 | 302824137         |      | Viešoji įstaiga Transporto kompetencijų agentūra                                                              | Susisiekimo ministerija
#|  216 | 132090925         |      | Valstybės įmonė Vidaus vandens kelių direkcija                                                                | Susisiekimo ministerija
#|  225 | 120721845         |      | AB "VIAMATIKA"                                                                                                | Susisiekimo ministerija
#|  226 | 140285526         |      | AB "Smiltynės perkėla"                                                                                        | Susisiekimo ministerija
#|  233 | 210060460         |      | Akcinė Bendrovė "Oro Navigacija"                                                                              | Susisiekimo ministerija
#|   99 | 188620589         |      | Lietuvos Respublikos susisiekimo ministerija                                                                  | Susisiekimo ministerija
#|   94 | 302308327         |      | Lietuvos Respublikos energetikos ministerija                                                                  | Energetikos ministerija
#|  213 | 305052228         |      | UAB „LTG Link“                                                                                                | Susisiekimo ministerija
#|  223 | 300149794         |      | VšĮ "Plačiajuostis internetas"                                                                                | Susisiekimo ministerija
#|   31 | 188784898         |      | Aplinkos apsaugos agentūra                                                                                    | Aplinkos ministerija
#|   48 | 288600210         |      | Valstybinė teritorijų planavimo ir statybos inspekcija prie Aplinkos ministerijos                             | Aplinkos ministerija
#|   49 | 188704927         |      | Nacionalinė žemės tarnyba prie Aplinkos ministerijos                                                          | Aplinkos ministerija
#|   56 | 123816152         |      | Lietuvos aplinkos apsaugos investicijų fondas                                                                 | Aplinkos ministerija
#|   71 | 188724381         |      | Valstybinė saugomų teritorijų tarnyba                                                                         | Aplinkos ministerija
#|   81 | 290743240         |      | Lietuvos hidrometeorologijos tarnyba prie Aplinkos ministerijos                                               | Aplinkos ministerija
#|   92 | 132340880         |      | Generalinė miškų urėdija prie Aplinkos ministerijos                                                           | Aplinkos ministerija
#|  249 | 00000111111       |      | Europos aplinkos agentūra                                                                                     | Aplinkos ministerija
#|  250 | 302470603         |      | Gamtos tyrimų centras                                                                                         | Aplinkos ministerija
#|  251 | 302470603         |      | Gamtos tyrimų centro Botanikos institutas                                                                     | Aplinkos ministerija
#|  255 | 190776346         |      | Lietuvos gamtos fondas                                                                                        | Aplinkos ministerija
#|  109 | 188602370         |      | Lietuvos Respublikos aplinkos ministerija                                                                     | Aplinkos ministerija
#|  111 | 188773688         |      | Klaipėdos rajono savivaldybės administracija                                                                  | Savivaldybės
#|   68 | 303004035         |      | VšĮ Būsto energijos taupymo agentūra                                                                          | Aplinkos ministerija
#|   98 | 302471705         |      | Valstybinė miškų tarnyba                                                                                      | Aplinkos ministerija
#|  197 | 304766622         |      | Aplinkos apsaugos departamentas prie Aplinkos ministerijos                                                    | Aplinkos ministerija
#|  125 | 305997589         |      | Viešoji įstaiga Statybos sektoriaus vystymo agentūra                                                          | Aplinkos ministerija
#|  169 | 288779560         |      | Lietuvos Respublikos aplinkos ministerijos Aplinkos projektų valdymo agentūra                                 | Aplinkos ministerija
#|  124 | 288724610         |      | Panevėžio miesto savivaldybės administracija                                                                  | Savivaldybės
#|  142 | 111952632         |      | Lietuvos teismo ekspertizės centras                                                                           | 
#|  148 | 188642660         |      | Biržų rajono savivaldybės administracija                                                                      | 
#|  155 | 288742590         |      | Prienų rajono savivaldybė                                                                                     | Savivaldybės
#|  156 | 188772814         |      | Šakių rajono savivaldybės administracija                                                                      | Savivaldybės
#|  158 | 190755028         |      | BĮ KLAIPĖDOS VALSTYBINIS MUZIKINIS TEATRAS                                                                    | 
#|  162 | 111102598         |      | Pakruojo rajono savivaldybė                                                                                   | Savivaldybės
#|  174 | 291993670         |      | Lietuvos geležinkelio profesinė sąjunga                                                                       | 
#|    9 | 124110246         |      | Valstybės įmonė Registrų centras                                                                              | Ekonomikos ir inovacijų ministerija
#|   19 | 193295631         |      | Lietuvos metrologijos inspekcija                                                                              | Ekonomikos ir inovacijų ministerija
#|   21 | 188770044         |      | Valstybinė vartotojų teisių apsaugos tarnyba                                                                  | Ekonomikos ir inovacijų ministerija
#|   27 | 124110246         |      | Valstybės įmonė Registrų centras                                                                              | Ekonomikos ir inovacijų ministerija
#|   46 | 124013427         |      | VšĮ Investuok Lietuvoje                                                                                       | Ekonomikos ir inovacijų ministerija
#|   75 | 193295631         |      | Matavimo priemonių registras                                                                                  | Ekonomikos ir inovacijų ministerija
#|   89 | 188711010         |      | Valstybinė metrologijos tarnyba                                                                               | Ekonomikos ir inovacijų ministerija
#|  149 | 188773916         |      | Kaišiadorių rajono savivaldybė                                                                                | Savivaldybės
#|  154 |         288742590 |      | Prienų rajono savivaldybė                                                                                     | 
#|  177 | 110068011         |      | VšĮ VALDYMO KOORDINAVIMO CENTRAS                                                                              | Ekonomikos ir inovacijų ministerija
#|  117 | 188706935         |      | Alytaus miesto savivaldybės administracija                                                                    | Savivaldybės
#|  143 | 302913276         |      | VšĮ CPO LT                                                                                                    | Ekonomikos ir inovacijų ministerija
#|  179 | 188730854         |      | Mokslo, inovacijų ir technologijų agentūra                                                                    | Ekonomikos ir inovacijų ministerija
#|  191 | 125447177         |      | Viešoji įstaiga Lietuvos verslo paramos agentūra                                                              | Ekonomikos ir inovacijų ministerija
#|  263 | 188708758         |      | Valstybinis turizmo departamentas                                                                             | Ekonomikos ir inovacijų ministerija
#|  269 | 188772433         |      | Informacinės visuomenės plėtros komitetas                                                                     | Ekonomikos ir inovacijų ministerija
#|  178 | 188621919         |      | Lietuvos Respublikos ekonomikos ir inovacijų ministerija                                                      | Ekonomikos ir inovacijų ministerija
#|    7 | 188711163         |      | LR valstybinė darbo inspekcija prie  Socialinės apsaugos ir darbo ministerijos                                | Socialinės apsaugos ir darbo ministerija
#|   51 | 188752021         |      | Valstybės vaiko teisių apsaugos ir įvaikinimo tarnyba prie Socialinės apsaugos ir darbo ministerijos          | Socialinės apsaugos ir darbo ministerija
#|   54 | 191717258         |      | Socialinių paslaugų priežiūros departamentas prie Socialinės apsaugos ir darbo ministerijos                   | Socialinės apsaugos ir darbo ministerija
#|   72 | 188725330         |      | Vaikų išlaikymo fondo administracija prie Socialinės apsaugos ir darbo ministerijos                           | Socialinės apsaugos ir darbo ministerija
#|   79 | 188711163         |      | Valstybinė darbo inspekcija                                                                                   | Socialinės apsaugos ir darbo ministerija
#|   84 | 191676548         |      | Neįgaliųjų reikalų departamentas prie Socialinės apsaugos ir darbo ministerijos                               | Socialinės apsaugos ir darbo ministerija
#|  107 | 190766619         |      | Lietuvos darbo birža prie Socialinės apsaugos ir darbo ministerijos                                           | Socialinės apsaugos ir darbo ministerija
#|  183 | 188681478         |      | Jaunimo reikalų departamentas prie Socialinės apsaugos ir darbo ministerijos                                  | Socialinės apsaugos ir darbo ministerija
#|    3 | 190766619         |      | Užimtumo tarnyba prie Lietuvos Respublikos socialinės apsaugos ir darbo ministerijos                          | Socialinės apsaugos ir darbo ministerija
#|   97 | 300121001         |      | Neįgalumo ir darbingumo nustatymo tarnyba prie Socialinės apsaugos ir darbo ministerijos                      | Socialinės apsaugos ir darbo ministerija
#|   53 | 191630223         |      | Valstybinio socialinio draudimo fondo valdyba prie Socialinės apsaugos ir darbo ministerijos                  | Socialinės apsaugos ir darbo ministerija
#|  189 | 190789945         |      | Techninės pagalbos neįgaliesiems centras prie Socialinės apsaugos ir darbo ministerijos                       | Socialinės apsaugos ir darbo ministerija
#|  193 | 192050725         |      | Europos socialinio fondo agentūra                                                                             | Socialinės apsaugos ir darbo ministerija
#|  200 | 300663201         |      | Marijampolės specialieji socialinės globos namai                                                              | Socialinės apsaugos ir darbo ministerija
#|  180 | 188603515         |      | Lietuvos Respublikos socialinės apsaugos ir darbo ministerija                                                 | Socialinės apsaugos ir darbo ministerija
#|   10 | 211950810         |      | VU Fizikos fakulteto  Branduolių ir elementariųjų dalelių fizikos centr                                       | Švietimo, mokslo ir sporto ministerija
#|   73 | 188620621         |      | Kūno kultūros ir sporto departamentas prie Lietuvos Respublikos Vyriausybės                                   | Švietimo, mokslo ir sporto ministerija
#|  100 | 305238040         |      | Nacionalinė švietimo agentūra                                                                                 | Švietimo, mokslo ir sporto ministerija
#|  115 | 111959192         |      | Studijų kokybės vertinimo centras                                                                             | Švietimo, mokslo ir sporto ministerija
#|  122 | 188780533         |      | Valstybinė lietuvių kalbos komisija                                                                           | Švietimo, mokslo ir sporto ministerija
#|  150 | 111959420         |      | Nacionalinis vėžio institutas                                                                                 | Švietimo, mokslo ir sporto ministerija
#|  172 | 111955023         |      | Lietuvių kalbos institutas                                                                                    | Švietimo, mokslo ir sporto ministerija
#|  173 | 111950396         |      | Vytauto Didžiojo universitetas                                                                                | Švietimo, mokslo ir sporto ministerija
#|  244 |         193201984 |      | Nacionalinis egzaminų centras                                                                                 | Švietimo, mokslo ir sporto ministerija
#|  252 | 211951150         |      | Klaipėdos universitetas                                                                                       | Švietimo, mokslo ir sporto ministerija
#|  266 | 211950810         |      | Vilniaus universitetas                                                                                        | Švietimo, mokslo ir sporto ministerija
#|  184 | 188603091         |      | Lietuvos Respublikos švietimo, mokslo ir sporto ministerija                                                   | Švietimo, mokslo ir sporto ministerija
#|   37 | 288700520         |      | Valstybinė kultūros paveldo komisija                                                                          | Kultūros ministerija
#|   44 | 188692688         |      | Kultūros paveldo departamentas prie Kultūros ministerijos                                                     | Kultūros ministerija
#|  141 | 190758095         |      | Klaipėdos apskrities Ievos Simonaitytės viešoji biblioteka                                                    | Kultūros ministerija
#|  144 | 300011619         |      | Koncertinė įstaiga Lietuvos nacionalinė filharmonija                                                          | Kultūros ministerija
#|  146 | 300038598         |      | Vilniaus pilių valstybinio kultūrinio rezervato direkcija                                                     | Kultūros ministerija
#|  163 | 190758138         |      | Kauno apskrities viešoji biblioteka                                                                           | Kultūros ministerija
#|  170 | 302297628         |      | Nacionalinis muziejus Lietuvos didžiosios kunigaikštystės Valdovų rūmai                                       | Kultūros ministerija
#|  203 | 190756087         |      | Lietuvos nacionalinis dailės muziejus                                                                         | Kultūros ministerija
#|  208 | 190757755         |      | Vilniaus apskrities Adomo Mickevičiaus viešoji biblioteka                                                     | Kultūros ministerija
#|  247 | 188756614         |      | Etninės kultūros globos taryba                                                                                | Kultūros ministerija
#|  264 | 190757374         |      | Valstybinis Vilniaus Gaono žydų muziejus                                                                      | Kultūros ministerija
#|  267 | 124247330         |      | VšĮ „Kultūros paveldo išsaugojimo pajėgos”                                                                    | Kultūros ministerija
#|  187 | 188683671         |      | Lietuvos Respublikos kultūros ministerija                                                                     | Kultūros ministerija
#|  218 | 190999616         |      | Respublinis priklausomybės ligų centras                                                                       | 
#|  234 | 188718528         |      | Alytaus rajono savivaldybės administracija                                                                    | Savivaldybės
#|   45 | 188697087         |      | Lietuvos vyriausiojo archyvaro tarnyba                                                                        | Kultūros ministerija
#|  157 | 190755028         |      | BĮ KLAIPĖDOS VALSTYBINIS MUZIKINIS TEATRAS                                                                    | Kultūros ministerija
#|  175 | 190755932         |      | Nacionalinis M. K. Čiurlionio dailės muziejus                                                                 | Kultūros ministerija
#|  229 | 190756653         |      | Maironio lietuvių literatūros muziejus                                                                        | Kultūros ministerija
#|  230 | 135163499         |      | Lietuvos sveikatos mokslų universiteto ligoninė Kauno klinikos                                                | 
#|   38 | 110057335         |      | VŠĮ Lietuvos žemės ūkio konsultavimo tarnyba                                                                  | Žemės ūkio ministerija
#|  106 | 288739270         |      | Nacionalinė mokėjimo agentūra prie Žemės ūkio ministerijos                                                    | Žemės ūkio ministerija
#|  120 | 306205513         |      | VĮ Žemės ūkio duomenų centras                                                                                 | Žemės ūkio ministerija
#|  134 | 306205513         |      | VĮ Žemės ūkio duomenų centras                                                                                 | Žemės ūkio ministerija
#|  248 | 00000000111       |      | EuroGeographics AISBL                                                                                         | Žemės ūkio ministerija
#|  253 | 302474021         |      | Lietuvos agrarinių ir miškų mokslų centro filialas Agrocheminių tyrimų laboratorija                           | Žemės ūkio ministerija
#|  241 | 188675190         |      | Lietuvos Respublikos žemės ūkio ministerija                                                                   | Žemės ūkio ministerija
#|  245 | 291993670         |      | Lietuvos Geležinkelio Profesinė Sąjunga                                                                       | 
#|  258 | 188774594         |      | Panevėžio rajono savivaldybės administracija                                                                  | Savivaldybės
#|  259 | 188769070         |      | Jonavos rajono savivaldybės administracija                                                                    | Savivaldybės
#|  260 | 188768545         |      | Kėdainių rajono savivaldybės administracija                                                                   | Savivaldybės
#|  261 | 188726247         |      | Radviliškio rajono savivaldybės administracija                                                                | Savivaldybės
#|  262 | 188710061         |      | Vilniaus miesto savivaldybės administracija                                                                   | Savivaldybės
#|  268 | 180390741         |      | VšĮ Regioninė Telšių ligoninė                                                                                 | 
#|  270 | 188774637         |      | Anykščių rajono savivaldybės administracija                                                                   | 
#|  271 | 188774637         |      | Anykščių rajono savivaldybės administracija                                                                   | 
#|  182 | 110084026         |      | UAB "Investicijų ir verslo garantijos"                                                                        | Verslas
#|  190 | 124361985         |      | Lietuvos šilumos tiekėjų asociacija                                                                           | Verslas
#|  165 | 188752740         |      | Žuvininkystės tarnyba prie Lietuvos Respublikos žemės ūkio ministerijos                                       | Žemės ūkio ministerija
#|  196 | 120505210         |      | AB Lietuvos radijo ir televizijos centras                                                                     | Verslas
#|  201 | 300021054         |      | UAB Laidotva                                                                                                  | Verslas
#|  205 | 121215587         |      | AB Lietuvos paštas                                                                                            | Verslas
#|  220 | 134170932         |      | AB "Detonas"                                                                                                  | Verslas
#|  246 | 121215434         |      | AB „Telia Lietuva“                                                                                            | Verslas
#|  273 |                   |      | Verslas                                                                                                       | 
#|   42 | 288692340         |      | Žurnalistų etikos inspektoriaus tarnyba                                                                       | Prezidentūrai ir Seimui atskaitingos institucijos
#|   43 | 188605295         |      | LIETUVOS RESPUBLIKOS SEIMAS                                                                                   | Prezidentūrai ir Seimui atskaitingos institucijos
#|  112 | 191428780         |      | Lietuvos gyventojų genocido ir rezistencijos tyrimo centras                                                   | Prezidentūrai ir Seimui atskaitingos institucijos
#|  235 | 188609016         |      | Lietuvos Respublikos Prezidento kanceliarija                                                                  | Prezidentūrai ir Seimui atskaitingos institucijos
#|  240 | 188668192         |      | Lietuvos Respublikos konkurencijos taryba                                                                     | Prezidentūrai ir Seimui atskaitingos institucijos
#|  274 |                   |      | Prezidentūrai ir Seimui atskaitingos institucijos                                                             | 
#|  254 | 100001111         |      | Lietuvos kariuomenės Juozo Vitkaus inžinerijos batalionas                                                     | Krašto apsaugos ministerija
#|  275 |                   |      | Krašto apsaugos ministerija                                                                                   | 
#|   18 | 188656261         |      | Viešųjų pirkimų tarnyba                                                                                       | Vyriausybei atskaitingos institucijos
#|   29 | 188604574         |      | Lietuvos Respublikos Vyriausybės kanceliarija                                                                 | Vyriausybei atskaitingos institucijos
#|   33 | 188601279         |      | Valstybinė maisto ir veterinarijos tarnyba                                                                    | Vyriausybei atskaitingos institucijos
#|   55 | 188607150         |      | Lietuvos Respublikos Vyriausioji rinkimų komisija                                                             | Prezidentūrai ir Seimui atskaitingos institucijos
#|   30 | 188607684         |      | Lietuvos bankas                                                                                               | Prezidentūrai ir Seimui atskaitingos institucijos
#|   50 | 188659229         |      | Lietuvos Respublikos valstybės kontrolė                                                                       | Prezidentūrai ir Seimui atskaitingos institucijos
#|   78 | 188600177         |      | Valstybės duomenų agentūra                                                                                    | Vyriausybei atskaitingos institucijos
#|  129 | 300845435         |      | Všį Vyriausybės strateginės analizės centras                                                                  | Vyriausybei atskaitingos institucijos
#|  167 | 193171427         |      | Vilniaus regioninis valstybės archyvas                                                                        | Vyriausybei atskaitingos institucijos
#|  194 | 188607912         |      | Valstybinė duomenų apsaugos inspekcija                                                                        | Vyriausybei atskaitingos institucijos
#|  199 | 305205389         |      | Vyriausybės atstovų įstaiga                                                                                   | Vyriausybei atskaitingos institucijos
#|  256 | 190764568         |      | Lietuvos valstybės istorijos archyvas                                                                         | Vyriausybei atskaitingos institucijos
#|  265 | 304937660         |      | VĮ "Energetikos agentūra"                                                                                     | Vyriausybei atskaitingos institucijos
#|  276 |                   |      | Vyriausybei atskaitingos institucijos                                                                         | 
#|  257 | 195727584         |      | Lietuvos vartotojų institutas                                                                                 | Nevyriausybinės organizacijos
#|   52 | 121442211         |      | Ryšių reguliavimo tarnyba                                                                                     | Vyriausybei atskaitingos institucijos
#| (276 rows)
