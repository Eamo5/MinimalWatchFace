import org.gradle.process.internal.ExecException

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.eamo5.minimalwatchface"
    compileSdk = libs.versions.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "com.eamo5.minimalwatchface"
        minSdk = libs.versions.minSdk.get().toInt()
        targetSdk = libs.versions.targetSdk.get().toInt()
        versionCode = libs.versions.versionCode.get().toInt()
        versionName = libs.versions.versionName.get()
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

tasks.register("validateWffXml") {
    val relativeDir = "../watchface-tools/third_party/wff"
    val buildTask = ":specification:validator:build"
    val jarFile = file(
        "$relativeDir/specification/validator/build/libs/dwf-format-2-validator-1.0.jar"
    )
    val inputFile = file("src/main/res/raw/watchface.xml")
    val validatorArgs = listOf("2", inputFile)

    doLast {
        // Validate that the relative directory exists
        val relativeDirFile = file(relativeDir)
        if (!relativeDirFile.exists() || !relativeDirFile.isDirectory) {
            throw GradleException(
                "The specified relative directory does not exist: $relativeDirFile"
            )
        }

        // Run the build task in the relative directory
        println("Running Gradle build task in $relativeDirFile...")
        exec {
            workingDir = relativeDirFile
            // Detect the platform-specific gradlew script
            val gradlewScript =
                if (System.getProperty("os.name").lowercase().contains("win")) {
                    "gradlew.bat"
                } else {
                    "./gradlew"
                }
            commandLine(gradlewScript, buildTask)
        }

        // Validate that the JAR file exists
        if (!jarFile.exists()) {
            throw GradleException("JAR file not found at ${jarFile.absolutePath}")
        }

        // Validate that the input file exists
        if (!inputFile.exists()) {
            throw GradleException("Input file not found at ${inputFile.absolutePath}")
        }

        // Run the resulting JAR file
        try {
            println("Running JAR file $jarFile with arguments: $validatorArgs")
            exec {
                commandLine(
                    "java", "-jar", jarFile.absolutePath, *validatorArgs.toTypedArray()
                )
            }
        } catch (e: ExecException) {
            throw GradleException("The JAR execution failed: ${e.message}. " +
                    "Check the JAR's output for more details.")
        }

    }
}
