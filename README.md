# Mirror на папки по WebDav

Първоначалната идея е за mirror на споделената папка с документи за проект, която се намира на
приложен тестови сървър в мрежа зад firewall. Единствения начин за разпространения на тази папка
навън е през сървър, на който има пуснат WebDav. В наличната ситуация не може да се изпозлва
rsync, което би било прекрасно решение.

След това, с цел разучаването на WebDav, което си е един application протокол върху HTTP е
направено и сваляне на файлове, само променените и нещо като обратен mirror. Това не се позлва
за споделената папка, но върши работа, например за сваляне на журнали.

Наличните към момента команди са:

За mirror на папка:

```bash
Usage: python -m davcli.mirror [OPTIONS] PATH DAVPATH

Options:
  -r, --upload       Реално качва променените файлове
  -t, --target TEXT  Базово URL зад което се прилага devpath префикса
  -u, --user TEXT    Потребител за достъп по webdav
  --password TEXT    Парола на потребителя; пита по подразбиране
  -v, --verbose      Отпечатва повече информация за комуникацията
  --proxy TEXT       Ако има нужда от прокси; формат host:port
```

За сваляне на промените от отдалечена папка:

```bash
Usage: python -m davcli.download [OPTIONS] DAVPATH COMMAND [ARGS]...

Options:
  --davhost TEXT              Базово URL на DaV сървъра
  --user TEXT                 Потребител за достъп по WebDav
  --password TEXT             Парола на потребителя; пита по подразбиране
  --proxy TEXT                Ако има нужда от прокси; формат host:port
  --verbose                   Отпечатва повече информация за комуникацията
  --recursive                 Обхожда рекурсивно Dav папките
  --pattern TEXT              Регулярен израз за включване на файла
  --swtrac-log-weeks INTEGER  Брой последните седмици за swtrac log

Commands:
  list  Извеждна списъка на файловете в DaV директорията
  sync  Сваля всички различни или липсващи файлове от WebDav
```

```bash
Usage: python -m davcli.download DAVPATH list [OPTIONS]

  Извеждна списъка на файловете в DaV директорията

Options:
  --dest DIRECTORY  Включва маркер дали файла в тази папка е различен
```

```bash
Usage: python -m davcli.download DAVPATH sync [OPTIONS] DEST

  Сваля всички различни или липсващи файлове от WebDav

Options:
  --append  Счита че файла само е нараствал (като log)
```

Информация за комуникатицията по стадарта WebDav може да се види тук:
[RFC4918](http://www.webdav.org/specs/rfc4918.html).

За изпозлването на range request в HTTP, в следната глава от описанието на HTTP:
[RFC9110](https://www.rfc-editor.org/rfc/rfc9110#name-range-requests).

vim:tw=96:et:ai
