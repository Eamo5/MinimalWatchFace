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

tasks.register("validateMemoryFootprint") {
    // Define the build variant dynamically
    val buildVariant = project.gradle.startParameter.taskNames
        .find { it.contains("Debug", ignoreCase = true) }?.let { "debug" }
        ?: project.gradle.startParameter.taskNames
            .find { it.contains("Release", ignoreCase = true) }?.let { "release" }
        ?: "release" // Default to debug if no variant is specified

    val relativeDirPath = "../watchface-tools/play-validations"
    val buildTask = ":memory-footprint:jar"
    val jarFile = file("$relativeDirPath/memory-footprint/build/libs/memory-footprint.jar")
    val outputApkFile = file(
        "build/outputs/apk/$buildVariant/watchface-$buildVariant.apk"
    )
    val intermediatesApkFile = file(
        "build/intermediates/apk/$buildVariant/watchface-$buildVariant.apk"
    )
    val schemaVersion = 2
    val ambientLimitMb = 10
    val activeLimitMb = 100
    val additionalArgs = listOf("--apply-v1-offload-limitations", "--estimate-optimization")

    doLast {
        val relativeDir = file(relativeDirPath)
        // Validate that the relative directory exists
        if (!relativeDir.exists() || !relativeDir.isDirectory) {
            throw GradleException("The specified relative directory does not exist: $relativeDir")
        }

        // Run the build task in the relative directory
        println("Running Gradle build task in $relativeDir...")
        exec {
            workingDir = relativeDir
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

        val apkFile = if (outputApkFile.exists()) {
            println("Found APK in preferred path: ${outputApkFile.absolutePath}")
            outputApkFile
        } else if (intermediatesApkFile.exists()) {
            println(
                "Preferred APK not found. Using fallback path: ${intermediatesApkFile.absolutePath}"
            )
            intermediatesApkFile
        } else {
            throw GradleException(
                """
                APK file not found in either of the following locations:
                - Preferred: ${outputApkFile.absolutePath}
                - Fallback: ${intermediatesApkFile.absolutePath}
                """.trimIndent()
            )
        }

        try {
            // Run the resulting JAR file
            println("Running JAR file $jarFile with arguments for APK: ${apkFile.absolutePath}")
            exec {
                commandLine(
                    "java", "-jar", jarFile.absolutePath,
                    "--watch-face", apkFile.absolutePath,
                    "--schema-version", schemaVersion.toString(),
                    "--ambient-limit-mb", ambientLimitMb.toString(),
                    "--active-limit-mb", activeLimitMb.toString(),
                    *additionalArgs.toTypedArray()
                )
            }
        } catch (e: ExecException) {
            throw GradleException(
                "The JAR execution failed with an error: ${e.message}. " +
                        "Please check the JAR's output for more details."
            )
        }
    }
}