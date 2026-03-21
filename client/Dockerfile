FROM maven:3.9.9-eclipse-temurin-17

WORKDIR /app

COPY pom.xml .
COPY src ./src

RUN mvn package -q

CMD ["java", "-jar", "target/client-1.0-SNAPSHOT.jar"]