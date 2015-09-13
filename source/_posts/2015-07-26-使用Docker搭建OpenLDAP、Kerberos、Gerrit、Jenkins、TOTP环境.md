title: 使用Docker搭建OpenLDAP、Kerberos、Gerrit、Jenkins、TOTP环境
id: docker-dev-env
date: 2015-07-26 01:12:34
tags:
---

## 背景

## OpenLDAP

Dockerfile
```Dockerfile
FROM ubuntu
RUN echo "deb http://mirrors.163.com/ubuntu/ trusty main restricted" > /etc/apt/sources.list
RUN apt-get update

RUN echo 'slapd/root_password password password' | debconf-set-selections &&\
    echo 'slapd/root_password_again password password' | debconf-set-selections && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y slapd ldap-utils

COPY files /tmp/ldap

EXPOSE 389

CMD slapd -h 'ldap:/// ldapi:///' -g openldap -u openldap -F /etc/ldap/slapd.d -d stats
```
初始化脚本
```sh
#!/usr/bin/env bash

cd /tmp/ldap

cat > back.ldif<<EOF
version: 1
changeType: add
dn: olcDatabase=hdb,cn=config
objectClass: olcDatabaseConfig
objectClass: olcHdbConfig
olcDatabase: {2}hdb
olcDbDirectory: /var/lib/ldap
olcSuffix: $DOMAIN_DN
olcAccess: {0}to attrs=userPassword,shadowLastChange by self write by anonymous auth by dn="$ADMIN_DN" write by * none
olcAccess: {1}to dn.base="" by * read
olcAccess: {2}to * by self write by dn="$ADMIN_DN" write by * read
olcLastMod: TRUE
olcRootDN: $ADMIN_DN
olcRootPW: $ADMIN_PW
olcDbCheckpoint: 512 30
olcDbConfig: {0}set_cachesize 0 2097152 0
olcDbConfig: {1}set_lk_max_objects 1500
olcDbConfig: {2}set_lk_max_locks 1500
olcDbConfig: {3}set_lk_max_lockers 1500
olcDbIndex: objectClass eq
EOF

cat > front.ldif<<EOF
dn: $DOMAIN_DN
dc: $NAME
objectClass: dcObject
objectClass: organizationalUnit
ou: $NAME

dn: ou=group,$DOMAIN_DN
objectClass: organizationalUnit
ou: group

dn: ou=user,$DOMAIN_DN
objectClass: organizationalUnit
ou: user

dn: ou=role,$DOMAIN_DN
objectClass: organizationalUnit
ou: role
EOF

service slapd start
ldapadd -Y EXTERNAL -H ldapi:/// -f back.ldif &&\
ldapadd -Y EXTERNAL -H ldapi:/// -f sssvlv_load.ldif &&\
ldapadd -Y EXTERNAL -H ldapi:/// -f sssvlv_config.ldif &&\
ldapadd -x -D $ADMIN_DN -w $ADMIN_PW -c -f front.ldif &&\
ldapadd -x -D $ADMIN_DN -w $ADMIN_PW -c -f more.ldif

date > /etc/ldap/created

rm -rf /tmp/ldap
```

```sh
DOMAIN_DN=dc=7v1,dc=net
ADMIN_DN=cn=admin,dc=7v1,dc=net
ADMIN_PW=1234
NAME=7v1
```

## Gerrit

### Dockerfile
```Dockerfile
FROM ubuntu

MAINTAINER lifei <lifei.vip@outlook.com>

RUN echo "deb http://mirrors.163.com/ubuntu/ trusty main restricted" > /etc/apt/sources.list
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y git-core

ENV GERRIT_USER gerrit2
ENV GERRIT_HOME /home/${GERRIT_USER}
ENV GERRIT_WAR ${GERRIT_HOME}/gerrit.war
ENV GERRIT_VERSION 2.11.2
RUN useradd -m ${GERRIT_USER}

COPY entrypoint.sh /entrypoint.sh
RUN chmod a+x /entrypoint.sh

COPY gerrit-${GERRIT_VERSION}.war $GERRIT_WAR
RUN chown -R ${GERRIT_USER}:${GERRIT_USER} $GERRIT_HOME

USER $GERRIT_USER
WORKDIR $GERRIT_HOME

ADD jre-8u51-linux-x64.gz /usr/lib/jvm/
ENV JAVA_HOME /usr/lib/jvm/jre1.8.0_51
ENV PATH $JAVA_HOME/bin:$PATH
RUN java -jar $GERRIT_WAR init --batch -d ${GERRIT_HOME}/gerrit

EXPOSE 8080 29418
CMD /entrypoint.sh

```

```sh
#!/usr/bin/env bash

$GERRIT_HOME/gerrit/bin/gerrit.sh start
if [ $? -eq 0 ]
then
    echo "gerrit $GERRIT_VERSION is started successfully."
	echo ""
	tail -f $GERRIT_HOME/gerrit/logs/httpd_log
else
    cat $GERRIT_HOME/gerrit/logs/error_log
fi
```

### 配置Gerrit使用LDAP认证
```ini
[auth]
    type = LDAP
[ldap]
    server = ldap://192.168.59.103
    sslVerify = false
    username = cn=admin,dc=7v1,dc=net
    password = 1234

    accountBase = ou=user,dc=7v1,dc=net
    accountPattern = (&(objectClass=inetOrgPerson)(uid=${username}))
    accountFullName = ${cn}

    groupBase = ou=user,dc=7v1,dc=net
    groupPattern = (cn=${groupname})
    groupMemberPattern = (uniqueMember=${dn})
```

`gerrit` 安装插件

把jar包拷贝到plugins文件夹下重启

## Kerberos

## OpenVPN

https://registry.hub.docker.com/u/kylemanna/openvpn/

## Google Authenticator(TOTP)跳板机

```Dockerfile

FROM ubuntu
RUN sed -i 's/http:\/\/archive\.ubuntu\.com\/ubuntu\//http:\/\/mirrors.163.com\/ubuntu\//' /etc/apt/sources.list
RUN sed -i 's/deb-src/# deb-src/' /etc/apt/sources.list
RUN apt-get update

RUN apt-get install -y ed ssh rsyslog fail2ban openssh-server openssh-client supervisor python-pyinotify libpam-google-authenticator && apt-get clean
ENV DEBIAN_FRONTEND noninteractive

# Enable google-auth
RUN sed -i '2i auth required pam_google_authenticator.so' /etc/pam.d/sshd
RUN sed -i 's/ChallengeResponseAuthentication no/ChallengeResponseAuthentication yes/' /etc/ssh/sshd_config

# Set up directories
RUN mkdir -p /var/run/sshd /var/log/supervisor /var/run/fail2ban

COPY fail2ban-supervisor.sh /usr/local/bin/
COPY supervisor.d/* /etc/supervisor/conf.d/
COPY fail2ban/* /etc/fail2ban/
CMD ["/usr/bin/supervisord","-c","/etc/supervisor/supervisord.conf"]
EXPOSE 22

```

## Jenkins

官方提供了Jenkins镜像
