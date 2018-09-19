import {MigrationInterface, QueryRunner} from "typeorm";
import * as fs from 'fs';
import * as path from 'path';

export class CategoryTree1537343350807 implements MigrationInterface {

    public async up(queryRunner: QueryRunner): Promise<any> {
      await queryRunner.query('DROP TABLE IF EXISTS scry2.categories cascade');
      await queryRunner.query('DROP TABLE IF EXISTS scry2.listings cascade');

      var dname =  path.join(__dirname, '../../../'+'db_migration/');
      let query = fs.readFileSync(dname+ 'category_tree_trigger.sql', "utf8")
      await queryRunner.query(query);
    }

    public async down(queryRunner: QueryRunner): Promise<any> {
    }

}
